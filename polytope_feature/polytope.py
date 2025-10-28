import logging
from typing import List

from .datacube.backends.datacube import Datacube
from .datacube.datacube_axis import UnsliceableDatacubeAxis
from .datacube.tensor_index_tree import TensorIndexTree
from .engine.hullslicer import HullSlicer
from .engine.optimised_point_in_polygon_slicer import OptimisedPointInPolygonSlicer
from .engine.optimised_quadtree_slicer import OptimisedQuadTreeSlicer
from .engine.point_in_polygon_slicer import PointInPolygonSlicer
from .engine.quadtree_slicer import QuadTreeSlicer
from .options import PolytopeOptions
from .shapes import ConvexPolytope, Point, Product
from .utility.combinatorics import group, tensor_product
from .utility.exceptions import AxisOverdefinedError
from .utility.list_tools import unique


class Request:
    """Encapsulates a request for data"""

    def __init__(self, *shapes):
        self.shapes = list(shapes)
        self.check_axes()

    def check_axes(self):
        """Check that all axes are defined by the combination of shapes, and that they are defined only once"""
        defined_axes = []

        for shape in self.shapes:
            for axis in shape.axes():
                if axis not in defined_axes:
                    defined_axes.append(axis)
                else:
                    raise AxisOverdefinedError(axis)

    def polytopes(self):
        """Returns the representation of the request as polytopes"""
        polytopes = []
        for shape in self.shapes:
            polytopes.extend(shape.polytope())
        return polytopes

    def __repr__(self):
        return_str = ""
        for shape in self.shapes:
            return_str += shape.__repr__() + "\n"
        return return_str


class Polytope:
    def __init__(
        self,
        datacube,
        options=None,
        engine_options=None,
        context=None,
    ):
        from .datacube import Datacube

        if options is None:
            options = {}
        if engine_options is None:
            engine_options = {}

        self.compressed_axes = []
        self.context = context

        (
            axis_options,
            compressed_axes_options,
            config,
            alternative_axes,
            grid_online_path,
            grid_local_directory,
        ) = PolytopeOptions.get_polytope_options(options)
        self.datacube = Datacube.create(
            datacube,
            config,
            axis_options,
            compressed_axes_options,
            alternative_axes,
            grid_online_path,
            grid_local_directory,
            self.context,
        )
        if engine_options == {}:
            for ax_name in self.datacube._axes.keys():
                engine_options[ax_name] = "hullslicer"
        self.engine_options = engine_options
        self.engines = self.create_engines()
        self.ax_is_unsliceable = {}

    def create_engines(self):
        engines = {}
        engine_types = set(self.engine_options.values())
        if "quadtree" in engine_types:
            # TODO: need to get the corresponding point cloud from the datacube
            quadtree_points = self.datacube.find_point_cloud()
            engines["quadtree"] = QuadTreeSlicer(quadtree_points)
        if "optimised_quadtree" in engine_types:
            # TODO: need to get the corresponding point cloud from the datacube
            quadtree_points = self.datacube.find_point_cloud()
            engines["optimised_quadtree"] = OptimisedQuadTreeSlicer(quadtree_points)
        if "hullslicer" in engine_types:
            engines["hullslicer"] = HullSlicer()
        if "point_in_polygon" in engine_types:
            points = self.datacube.find_point_cloud()
            engines["point_in_polygon"] = PointInPolygonSlicer(points)
        if "optimised_point_in_polygon" in engine_types:
            points = self.datacube.find_point_cloud()
            engines["optimised_point_in_polygon"] = OptimisedPointInPolygonSlicer(points)
        return engines

    def _unique_continuous_points(self, p: ConvexPolytope, datacube: Datacube):
        for i, ax in enumerate(p._axes):
            mapper = datacube.get_mapper(ax)
            if self.ax_is_unsliceable.get(ax, None) is None:
                self.ax_is_unsliceable[ax] = isinstance(mapper, UnsliceableDatacubeAxis)
            if self.ax_is_unsliceable[ax]:
                break
            for j, val in enumerate(p.points):
                p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
        # Remove duplicate points
        unique(p.points)

    def slice(self, datacube, polytopes: List[ConvexPolytope]):
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""

        # TODO: if polytope has measure 0 and if we have a higher-dimensional slicer, then keep the polytope as a
        # TODO: higher-dim object somehow keep that polytope tagged with measure 0 as well, so we can then take
        # TODO: alternative slicing mechanism
        self.find_compressed_axes(datacube, polytopes)

        self.remove_compressed_axis_in_union(polytopes)

        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
            if isinstance(p, Product):
                for poly in p.polytope():
                    self._unique_continuous_points(poly, datacube)
            else:
                self._unique_continuous_points(p, datacube)

        groups, input_axes = group(polytopes)
        datacube.validate(input_axes)
        request = TensorIndexTree()
        combinations = tensor_product(groups)

        # NOTE: could optimise here if we know combinations will always be for one request.
        # Then we do not need to create a new index tree and merge it to request, but can just
        # directly work on request and return it...

        for c in combinations:
            r = TensorIndexTree()
            new_c = []
            for combi in c:
                if isinstance(combi, list):
                    new_c.extend(combi)
                else:
                    new_c.append(combi)
            final_polys = []
            for poly in new_c:
                if isinstance(poly, Product):
                    final_polys.extend(poly.polytope())
                else:
                    final_polys.append(poly)
            r["unsliced_polytopes"] = set(final_polys)
            current_nodes = [r]
            for ax in datacube.axes.values():
                engine = self.find_engine(ax)
                next_nodes = []
                interm_next_nodes = []
                for node in current_nodes:
                    engine._build_branch(ax, node, datacube, interm_next_nodes, self)
                    next_nodes.extend(interm_next_nodes)
                    interm_next_nodes = []
                current_nodes = next_nodes

            request.merge(r)
        return request

    def find_engine(self, ax):
        slicer_type = self.engine_options[ax.name]
        return self.engines[slicer_type]

    def switch_polytope_dim(self, request):
        # If we see a 2-dim slicer on an axis
        # then make sure that if the shape is a point, we set decompose_1D to False
        for ax, slicer in self.engine_options.items():
            if slicer == "quadtree":
                for shp in request.shapes:
                    if ax in shp.axes() and isinstance(shp, Point):
                        shp.decompose_1D = False

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        logging.info("Starting request for %s ", self.context)
        self.datacube.check_branching_axes(request)
        self.switch_polytope_dim(request)
        for polytope in request.polytopes():
            method = polytope.method
            if method == "nearest":
                if polytope.is_flat:
                    if self.datacube.nearest_search.get(tuple(polytope.axes()), None) is None:
                        self.datacube.nearest_search[tuple(polytope.axes())] = polytope.values
                    else:
                        self.datacube.nearest_search[tuple(polytope.axes())].append(polytope.values[0])
                else:
                    if self.datacube.nearest_search.get(tuple(polytope.axes()), None) is None:
                        self.datacube.nearest_search[tuple(polytope.axes())] = polytope.points
                    else:
                        self.datacube.nearest_search[tuple(polytope.axes())].append(polytope.points[0])
        request_tree = self.slice(self.datacube, request.polytopes())
        logging.info("Created request tree for %s ", self.context)
        self.datacube.get(request_tree, self.context)
        logging.info("Retrieved data for %s ", self.context)
        return request_tree

    def find_compressed_axes(self, datacube, polytopes):
        # First determine compressable axes from input polytopes
        compressable_axes = []
        for polytope in polytopes:
            if polytope.is_orthogonal:
                for ax in polytope.axes():
                    compressable_axes.append(ax)
        # Cross check this list with list of compressable axis from datacube
        # (should not include any merged or coupled axes)
        for compressed_axis in compressable_axes:
            if compressed_axis in datacube.compressed_axes:
                self.compressed_axes.append(compressed_axis)

        k, last_value = _, datacube.axes[k] = datacube.axes.popitem()
        self.compressed_axes.append(k)

    def remove_compressed_axis_in_union(self, polytopes):
        for p in polytopes:
            if p.is_in_union:
                for axis in p.axes():
                    if axis in self.compressed_axes:
                        if axis == self.compressed_axes[-1]:
                            self.compressed_axes.remove(axis)
