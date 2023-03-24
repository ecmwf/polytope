from typing import List

from ..datacube.datacube import Datacube
from ..shapes import ConvexPolytope

class Engine():

    def __init__(self):
        pass

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        pass

    @staticmethod
    def default():
        from .hullslicer import HullSlicer
        return HullSlicer()

