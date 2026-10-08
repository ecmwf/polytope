import logging
from typing import List

from .datacube.backends.datacube import Datacube
from .datacube.datacube_axis import UnsliceableDatacubeAxis
from .datacube.tensor_index_tree import TensorIndexTree
from .datacube.tree_rows import RowMerger
from .engine.hullslicer import HullSlicer
from .engine.optimised_point_in_polygon_slicer import OptimisedPointInPolygonSlicer
from .engine.optimised_quadtree_slicer import OptimisedQuadTreeSlicer
from .engine.point_in_polygon_slicer import PointInPolygonSlicer
from .engine.quadtree_slicer import QuadTreeSlicer
from .options import PolytopeOptions
from .shapes import ConvexPolytope, Point, Product, Union
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
        context=None,
    ):
        from .datacube import Datacube

        if options is None:
            options = {}

        self.compressed_axes = []
        self.context = context

        (
            axis_options,
            compressed_axes_options,
            config,
            alternative_axes,
            use_catalogue,
            engine_options,
            bulk_grid_leaves,
        ) = PolytopeOptions.get_polytope_options(options)
        self.datacube = Datacube.create(
            datacube,
            config,
            axis_options,
            compressed_axes_options,
            alternative_axes,
            use_catalogue,
            self.context,
        )
        self.datacube.bulk_grid_leaves = bulk_grid_leaves
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

        for engine in set(self.engines.values()):
            engine.reset()

        self.find_compressed_axes(datacube, polytopes)
        # the last datacube axis holds the tree leaves (e.g. longitude); the slicer stores those as numpy arrays
        self.leaf_axis_name = next(reversed(datacube.axes.keys()))

        merge_rows = self._compress_union_rows(datacube, polytopes)

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
        row_merger = RowMerger(self.leaf_axis_name) if merge_rows else None

        axes = list(datacube.axes.values())
        engines = [self.find_engine(ax) for ax in axes]
        batched_axes = {ax.name for ax, engine in zip(axes, engines) if engine.batches_polytopes}

        for shared, batched in self._group_combinations(tensor_product(groups), batched_axes):
            r = TensorIndexTree()
            r["unsliced_polytopes"] = set(shared)
            current_nodes = [r]
            for ax, engine in zip(axes, engines):
                if engine.batches_polytopes:
                    # The prefix is shared by every grouped combination, so hand all of
                    # their polytopes on this engine's axes to it at once.
                    for node in current_nodes:
                        node["unsliced_polytopes"] = node["unsliced_polytopes"] | batched
                next_nodes = []
                for node in current_nodes:
                    engine._build_branch(ax, node, datacube, next_nodes, self)
                current_nodes = next_nodes

            if row_merger is None:
                request.merge(r)
            else:
                row_merger.merge(request, r)
        if row_merger is not None:
            row_merger.finalise(request)
        return request

    # Off by default: the legacy CovJSON step encoder (covjsonkit ``walk_tree_step``, used for climate-dt polygons)
    # reads one point per leaf.  Set to True on an instance (or the class) to get one leaf per row for polygons/paths.
    _merge_union_rows = False

    def _compress_union_rows(self, datacube, polytopes):
        """Apply ``remove_compressed_axis_in_union`` unless the union's rows can be merged instead.

        A union of non-orthogonal shapes (the convex pieces of a polygon, the segments of a path) used to leave the
        leaf axis uncompressed, i.e. one tree node per point.  When the leaf axis holds array leaves and every piece
        has the same tag (so per-point tags carry no information), it stays compressed and the pieces' leaves are
        merged row by row (see ``tree_rows.RowMerger``).  Returns whether rows must be merged.
        """
        before = list(self.compressed_axes)
        self.remove_compressed_axis_in_union(polytopes)
        leaf = self.leaf_axis_name
        if not self._merge_union_rows or leaf not in before or leaf in self.compressed_axes:
            return False
        if self.engine_options.get(leaf) != "hullslicer":
            return False
        if not HullSlicer.is_array_leaf_axis(datacube.axes[leaf], self):
            return False
        pieces = []
        for p in polytopes:
            pieces.extend(p.polytope() if isinstance(p, Product) else [p])
        tags = {p.tag for p in pieces if p.is_in_union and leaf in p.axes()}
        if len(tags) > 1:
            return False
        self.compressed_axes = before
        return True

    @staticmethod
    def _flatten_combination(combination):
        polys = []
        for combi in combination:
            for poly in combi if isinstance(combi, list) else [combi]:
                if isinstance(poly, Product):
                    polys.extend(poly.polytope())
                else:
                    polys.append(poly)
        return polys

    @classmethod
    def _group_combinations(cls, combinations, batched_axes):
        """Yield (shared_polytopes, batched_polytopes) per distinct tree prefix.

        Polytopes on axes of a batching engine (see Engine.batches_polytopes) are split
        off; combinations whose remaining polytopes are identical (eg. every Point of a
        Union shares the same Selects) then only need their prefix built once.
        """
        grouped = {}
        for c in combinations:
            shared, batched = [], []
            for poly in cls._flatten_combination(c):
                (batched if batched_axes.intersection(poly.axes()) else shared).append(poly)
            key = frozenset(shared) if batched_axes else object()
            entry = grouped.setdefault(key, (shared, set()))
            entry[1].update(batched)
        return grouped.values()

    def find_engine(self, ax):
        if ax.name not in self.engine_options:
            raise ValueError(f"No engine specified for axis {ax.name}")
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
                    elif isinstance(shp, Union):
                        for s in shp._shapes:
                            if ax in s.axes() and isinstance(s, Point):
                                s.decompose_1D = False

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        logging.info("Starting request for %s ", self.context)
        self.datacube.check_branching_axes(request)
        self.switch_polytope_dim(request)
        self.datacube.nearest_search = {}
        for polytope in request.polytopes():
            if polytope.method == "nearest":
                # Register the query point(s) with the tag of the polytope they come from, so the
                # backend can attach the right tag to each nearest point once it is resolved.
                query_points = polytope.values if polytope.is_flat else polytope.points
                points, _, tags = self.datacube.nearest_search.setdefault(tuple(polytope.axes()), ([], polytope.k, []))
                points.extend(list(pt) for pt in query_points)
                tags.extend([polytope.tag] * len(query_points))
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
