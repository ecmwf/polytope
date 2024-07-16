from abc import abstractmethod
from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope
from ..utility.combinatorics import unique


class Engine:
    def __init__(self, engine_options=None):
        if engine_options is None:
            engine_options = {}
        self.engine_options = engine_options

        # self.ax_is_unsliceable = {}
        self.axis_values_between = {}
        self.sliced_polytopes = {}
        self.remapped_vals = {}
        self.compressed_axes = []

    # def _unique_continuous_points(self, p: ConvexPolytope, datacube: Datacube):
    #     for i, ax in enumerate(p._axes):
    #         mapper = datacube.get_mapper(ax)
    #         if self.ax_is_unsliceable.get(ax, None) is None:
    #             self.ax_is_unsliceable[ax] = isinstance(mapper, UnsliceableDatacubeAxis)
    #         if self.ax_is_unsliceable[ax]:
    #             break
    #         for j, val in enumerate(p.points):
    #             p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
    #     # Remove duplicate points
    #     unique(p.points)

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> TensorIndexTree:
        # Delegate to the right slicer that the axes within the polytopes need to use
        pass

    def check_slicer(self, ax):
        # Return the slicer instance if ax is sliceable.
        # If the ax is unsliceable, return None.
        if isinstance(ax, UnsliceableDatacubeAxis):
            return None
        slicer_type = self.engine_options[ax.name]
        slicer = self.generate_slicer(slicer_type)
        return slicer

    # def generate_slicer(self, slicer_type):
    #     # TODO: instantiate the slicer (hullslicer or quadtree) instance
    #     pass

    # def determine_slicer(self, ax):
    #     pass

    # def build_unsliceable_node(self):
    #     pass

    @staticmethod
    def default():
        from .hullslicer import HullSlicer

        return HullSlicer()

    @abstractmethod
    def _build_branch(self, ax, node, datacube, next_nodes):
        pass
