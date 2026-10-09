from abc import abstractmethod
from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope


class Engine:
    # When True, the engine resolves *all* polytopes defined on its axes in a single
    # pass on a node (eg. the quadtree slicer resolving lat/lon jointly into one bulk
    # leaf). Polytope.slice() can then share the tree prefix built by the other
    # engines across every request combination that only differs on this engine's
    # axes (eg. a Union of many Points), and hand all of those combinations'
    # polytopes to this engine at once instead of rebuilding the prefix per point.
    batches_polytopes = False

    def batches_polytope(self, polytope, datacube, api=None):
        """Whether this engine resolves ``polytope`` in a batch rather than one tree descent per polytope.

        Per polytope, because an engine can batch some of the polytopes on its axes and not others: the
        hullslicer resolves nearest ``Point`` queries on a structured grid's two axes in one pass
        (:mod:`polytope_feature.engine.nearest_grid`) and everything else one descent at a time.
        """
        return self.batches_polytopes

    def reset(self):
        """Clear any per-slice state. Called once at the start of every Polytope.slice()."""
        pass

    def __init__(self, engine_options=None):
        if engine_options is None:
            engine_options = {}
        self.engine_options = engine_options
        self.ax_is_unsliceable = {}

        self.axis_values_between = {}
        self.sliced_polytopes = {}
        self.remapped_vals = {}
        self.compressed_axes = []

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

    @staticmethod
    def default():
        from .hullslicer import HullSlicer

        return HullSlicer()

    @abstractmethod
    def _build_branch(self, ax, node, datacube, next_nodes, api):
        pass
