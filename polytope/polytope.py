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


class Polytope:
    def __init__(self, datacube, engine=None, options=None):
        from .datacube import Datacube
        from .engine import Engine

        if options is None:
            options = {}

        axis_options, compressed_axes_options, config, alternative_axes = PolytopeOptions.get_polytope_options(options)

        self.datacube = Datacube.create(datacube, config, axis_options, compressed_axes_options, alternative_axes)
        self.engine = engine if engine is not None else Engine.default()
        self.time = 0

    def slice(self, polytopes: List[ConvexPolytope]):
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""
        return self.engine.extract(self.datacube, polytopes)

    def retrieve(self, request: Request, method="standard", context=None):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        if context is None:
            context = {}
        logging.info("Starting request for %s ", context)
        self.datacube.check_branching_axes(request)
        request_tree = self.engine.extract(self.datacube, request.polytopes())
        logging.info("Created request tree for %s ", context)
        self.datacube.get(request_tree, context)
        logging.info("Retrieved data for %s ", context)
        return request_tree
