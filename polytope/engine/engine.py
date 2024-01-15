from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.index_tree import IndexTree
from ..shapes import ConvexPolytope


class Engine:
    def __init__(self, engine_options=None):
        if engine_options is None:
            engine_options = {}
        self.engine_options = engine_options
        pass

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> IndexTree:
        # Relegate to the right slicer that the axes within the polytopes need to use

        # NOTE: the quadtree slicer is fixed 2D for now so it can only be used if the two axes used are specified as
        # quadtree

        # NOTE: can different hullslicers be used on axes within the same polytope?

        # TODO: how do we pass in the option of which axes are with which slicer?
        pass

    def extract_test(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> IndexTree:
        # build final return index tree here

        request = IndexTree()

        combinations = self.find_polytope_combinations(datacube, polytopes)

        for c in combinations:
            r = IndexTree()
            r["unsliced_polytopes"] = set(c)
            current_nodes = [r]
            for ax in datacube.axes.values():
                # TODO: is this what we want to do?
                # TODO: when do we defer to the different slicer types?

                # TODO: need first to determine here which slicer should be used for this axis.
                # TODO: If the slicer is quadtree, need to ensure that the other associated axis is also of type quadtree
                # TODO: Here, could also directly check the slicing for unsliceable axes
                next_nodes = []
                for node in current_nodes:
                    self._build_branch(ax, node, datacube, next_nodes)
                current_nodes = next_nodes
            request.merge(r)
        return request

    def check_slicer(self, ax):
        # Return the slicer instance if ax is sliceable.
        # If the ax is unsliceable, return None.
        if isinstance(ax, UnsliceableDatacubeAxis):
            return None
        slicer_type = self.engine_options[ax.name]
        slicer = self.generate_slicer(slicer_type)
        return slicer

    def generate_slicer(self, slicer_type):
        # TODO: instantiate the slicer (hullslicer or quadtree) instance
        pass

    def determine_slicer(self, ax):
        pass

    def build_unsliceable_node(self):
        pass

    @staticmethod
    def default():
        from .hullslicer import HullSlicer

        return HullSlicer()
