from typing import List

from .datacube.index_tree import IndexTree
from .engine.hullslicer import HullSlicer
from .engine.quadtree_slicer import QuadTreeSlicer
from .shapes import ConvexPolytope
from .utility.engine_tools import find_polytope_combinations
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


class Polytope:
    def __init__(
        self,
        datacube,
        engine=None,
        axis_options=None,
        datacube_options=None,
        engine_options=None,
        point_cloud_options=None,
    ):
        from .datacube import Datacube
        from .engine import Engine

        if axis_options is None:
            axis_options = {}
        if datacube_options is None:
            datacube_options = {}
        if engine_options is None:
            engine_options = {}

        self.datacube = Datacube.create(datacube, axis_options, point_cloud_options=point_cloud_options)
        self.engine = engine if engine is not None else Engine.default()
        if engine_options == {}:
            for ax_name in self.datacube._axes.keys():
                engine_options[ax_name] = "hullslicer"
        self.engine_options = engine_options
        self.engines = self.create_engines()

    def create_engines(self):
        engines = {}
        engine_types = set(self.engine_options.values())
        if "quadtree" in engine_types:
            # quadtree_axes = [key for key in self.engine_options.keys() if self.engine_options[key] == "quadtree"]
            # TODO: need to get the corresponding point cloud from the datacube
            quadtree_points = self.datacube.find_point_cloud()
            engines["quadtree"] = QuadTreeSlicer(quadtree_points)
        if "hullslicer" in engine_types:
            engines["hullslicer"] = HullSlicer()
        return engines

    def slice(self, polytopes: List[ConvexPolytope]):
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""

        combinations = find_polytope_combinations(self.datacube, polytopes)

        request = IndexTree()

        for c in combinations:
            r = IndexTree()
            r["unsliced_polytopes"] = set(c)
            current_nodes = [r]
            for ax in self.datacube.axes.values():
                # determine the slicer for each axis
                engine = self.find_engine(ax)

                # TODO: what happens when we have a quadtree engine and we handle two axes at once??
                # Need to build the two axes nodes as just one node within the slicer engine...

                next_nodes = []
                for node in current_nodes:
                    print(node)
                    engine._build_branch(ax, node, self.datacube, next_nodes)
                current_nodes = next_nodes
            request.merge(r)

        # TODO: return tree
        # return self.engine.extract(self.datacube, polytopes)
        request.pprint()
        return request

    def find_engine(self, ax):
        slicer_type = self.engine_options[ax.name]
        return self.engines[slicer_type]

    def old_retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        request_tree = self.engine.extract(self.datacube, request.polytopes())
        self.datacube.get(request_tree)
        return request_tree

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        request_tree = self.slice(request.polytopes())
        self.datacube.get(request_tree)
        return request_tree
