from .utility.combinatorics import group, tensor_product
from .utility.list_tools import unique
from .engine.quadtree_slicer import QuadTreeSlicer
from .engine.hullslicer import HullSlicer
from .datacube.tensor_index_tree import TensorIndexTree
from .datacube.datacube_axis import UnsliceableDatacubeAxis
from .datacube.backends.datacube import Datacube
import logging
from typing import List

from .options import PolytopeOptions
from .shapes import ConvexPolytope
from .utility.exceptions import AxisOverdefinedError


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


# class Polytope:
#     def __init__(self, datacube, engine=None, options=None, context=None):
#         from .datacube import Datacube
#         from .engine import Engine

#         if options is None:
#             options = {}

#         axis_options, compressed_axes_options, config, alternative_axes = PolytopeOptions.get_polytope_options(options)

#         self.context = context

#         self.datacube = Datacube.create(
#             datacube, config, axis_options, compressed_axes_options, alternative_axes, self.context
#         )
#         self.engine = engine if engine is not None else Engine.default()
#         self.time = 0

#     def slice(self, polytopes: List[ConvexPolytope]):
#         """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""
#         return self.engine.extract(self.datacube, polytopes)

#     def retrieve(self, request: Request, method="standard"):
#         """Higher-level API which takes a request and uses it to slice the datacube"""
#         logging.info("Starting request for %s ", self.context)
#         self.datacube.check_branching_axes(request)
#         request_tree = self.engine.extract(self.datacube, request.polytopes())
#         logging.info("Created request tree for %s ", self.context)
#         self.datacube.get(request_tree, self.context)
#         logging.info("Retrieved data for %s ", self.context)
#         return request_tree


class Polytope:
    def __init__(
        self,
        request,
        datacube,
        options=None,
        engine_options=None,
        point_cloud_options=None,
        context=None,
    ):
        from .datacube import Datacube

        if options is None:
            options = {}
        if engine_options is None:
            engine_options = {}

        self.compressed_axes = []
        self.context = context

        axis_options, compressed_axes_options, config, alternative_axes = PolytopeOptions.get_polytope_options(options)
        self.datacube = Datacube.create(
            request,
            datacube,
            config,
            axis_options,
            compressed_axes_options,
            point_cloud_options,
            alternative_axes,
            self.context
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
        if "hullslicer" in engine_types:
            engines["hullslicer"] = HullSlicer()
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

        self.find_compressed_axes(datacube, polytopes)

        self.remove_compressed_axis_in_union(polytopes)

        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
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
            r["unsliced_polytopes"] = set(new_c)
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

    def old_retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        # self.datacube.check_branching_axes(request)
        request_tree = self.engine.extract(self.datacube, request.polytopes())
        self.datacube.get(request_tree)
        return request_tree

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        request_tree = self.slice(self.datacube, request.polytopes())
        self.datacube.get(request_tree)
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
                    if axis == self.compressed_axes[-1]:
                        self.compressed_axes.remove(axis)
