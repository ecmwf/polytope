from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope


class Engine:
    def __init__(self):
        pass

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> TensorIndexTree:
        pass

    @staticmethod
    def default():
        from .hullslicer import HullSlicer

        return HullSlicer()
