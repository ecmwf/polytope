import numpy as np
from earthkit import data

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingEra5Data:
    def setup_method(self, method):
        ds = data.from_source("file", "./tests/data/era5-levels-members.grib")
        array = ds.to_xarray().isel(step=0).t
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_2D_box(self):
        request = Request(
            Box(["number", "isobaricInhPa"], [3, 0.0], [6, 1000.0]),
            Select("time", ["2017-01-02T12:00:00"]),
            Box(["latitude", "longitude"], lower_corner=[10.0, 0.0], upper_corner=[0.0, 30.0]),
            Select("step", [np.timedelta64(0, "s")]),
        )

        result = self.API.retrieve(request)
        result.pprint()

        assert len(result.leaves) == 4 * 1 * 2 * 4 * 11
