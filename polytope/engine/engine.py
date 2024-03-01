from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.index_tree import IndexTree
from ..shapes import ConvexPolytope


class Engine:
    def __init__(self):
        pass

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> IndexTree:
        pass

    @staticmethod
    def default():
        from .hullslicer import HullSlicer

        return HullSlicer()
