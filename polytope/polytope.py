from typing import List

from .shapes import ConvexPolytope
from .utility.exceptions import AxisOverdefinedError
from .utility.engine_tools import find_polytope_combinations


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
    def __init__(self, datacube, engine=None, axis_options={}):
        from .datacube import Datacube
        from .engine import Engine

        self.datacube = Datacube.create(datacube, axis_options)
        self.engine = engine if engine is not None else Engine.default()

    def slice(self, polytopes: List[ConvexPolytope]):
        # TODO: In this function, create final index tree
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""

        # TODO: find the possible polytope combinations
        combinations = find_polytope_combinations(self.datacube, polytopes)

        # TODO: start building tree

        # TODO: iterate over the combinations and then the axes in the datacube

        # TODO: determine the slicer for each axis

        # TODO: build node in tree for the sliced values and update next_nodes

        # TODO: return tree
        return self.engine.extract(self.datacube, polytopes)

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        request_tree = self.engine.extract(self.datacube, request.polytopes())
        self.datacube.get(request_tree)
        return request_tree
