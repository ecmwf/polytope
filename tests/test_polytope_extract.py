from polytope.polytope import Polytope

import numpy as np
import pandas as pd
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.datacube.index_tree import IndexTree
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import (
    Box,
    ConvexPolytope,
    Disk,
    PathSegment,
    Polygon,
    Select,
    Span,
    Union,
)


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(6, 129, 100, 100),
            dims=("step", "level", "lat", "lon"),
            coords={
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "lat": range(0, 100),
                'lon': range(0, 100),
            },
        )
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.engine_options = {"step": "hullslicer",
                               "level": "hullslicer",
                               "lat": "quadtree",
                               "lon": "quadtree"}
        self.API = Polytope(datacube=array, engine=self.slicer, engine_options=self.engine_options)

    # Testing different shapes

    def test_2D_box(self):
        request = Request(Box(["step", "level"], [3, 10], [6, 11]), Box(["lat", "lon"], [0, 0], [20, 20]))
        result = self.API.retrieve(request)

        result.pprint()
        assert len(result.leaves) == 4
