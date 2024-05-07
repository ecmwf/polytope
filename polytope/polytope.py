from typing import List

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
    def __init__(self, datacube, engine=None, axis_options=None, datacube_options=None):
        from .datacube import Datacube
        from .engine import Engine

        if axis_options is None:
            axis_options = {}
        if datacube_options is None:
            datacube_options = {}

        self.datacube = Datacube.create(datacube, axis_options)
        self.engine = engine if engine is not None else Engine.default()

    def slice(self, polytopes: List[ConvexPolytope]):
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""
        return self.engine.extract(self.datacube, polytopes)

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        for polytope in request.polytopes():
            if polytope.is_natively_1D:
                for ax in polytope.axes():
                    if ax not in self.datacube.merged_axes:
                        # self.datacube.compressed_axes.extend(polytope.axes())
                        self.datacube.compressed_axes.append(ax)
                # print(self.datacube.compressed_axes)
        # TODO: remove grid axes from the possible compressed_axes
        all_datacube_coupled_axes = []
        for coupled_axes in self.datacube.coupled_axes:
            # NOTE: the last axis from the coupled axes can always be compressed? Causes problems to fetch data
            # using pygribjump
            all_datacube_coupled_axes.extend(coupled_axes)
        self.datacube.compressed_axes = [
            ax for ax in self.datacube.compressed_axes if ax not in all_datacube_coupled_axes
        ]

        # for ax in self.datacube.coupled_axes:
        #     self.datacube.compressed_axes.remove(ax)
        request_tree = self.engine.extract(self.datacube, request.polytopes())
        self.datacube.get(request_tree)
        return request_tree
