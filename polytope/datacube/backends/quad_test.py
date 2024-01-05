# TODO: create quadtree from a set of 2D points with each leaf containing exactly one data point
from .datacube import Datacube


class IrregularGridDatacube(Datacube):
    def __init__(self, points, config={}, axis_options={}):
        self.points = points

    def lat_points(self):
        return [p[0] for p in self.points]

    def lon_points(self):
        return [p[1] for p in self.points]
