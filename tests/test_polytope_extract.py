import numpy as np
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box


class TestPolytopeExtract:
    def setup_method(self, method):
        # TODO: this doesn't create an irregular grid mapper??
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(6, 129, 100, 100),
            dims=("step", "level", "latitude", "longitude"),
            coords={
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "latitude": range(0, 100),
                "longitude": range(0, 100),
            },
        )
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.engine_options = {
            "step": "hullslicer",
            "level": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
        }
        quadtree_points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        self.options = {
            "values": {"mapper": {"type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}},
        }
        self.API = Polytope(
            datacube=array,
            engine=self.slicer,
            axis_options=self.options,
            engine_options=self.engine_options,
            point_cloud_options=quadtree_points,
        )

    # Testing different shapes

    def test_2D_box(self):
        request = Request(Box(["step", "level"], [3, 10], [6, 11]), Box(["latitude", "longitude"], [0, 0], [20, 20]))
        result = self.API.retrieve(request)

        result.pprint()
        assert len(result.leaves) == 12
