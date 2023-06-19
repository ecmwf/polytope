import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select
from polytope.utility.exceptions import UnsliceableShapeError


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # create a dataarray with 3 labelled axes using different index types
        dims = np.random.randn(3, 1, 129)
        array = xr.Dataset(
            data_vars=dict(param=(["date", "variable", "level"], dims)),
            coords={"date": pd.date_range("2000-01-01", "2000-01-03", 3), "variable": ["a"], "level": range(1, 130)},
        )
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    # Testing different shapes

    def test_finding_existing_variable(self):
        request = Request(Box(["level"], [10], [11]), Select("date", ["2000-01-01"]), Select("variable", ["a"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 2

    def test_finding_nonexisting_variable(self):
        request = Request(Box(["level"], [10], [11]), Select("date", ["2000-01-01"]), Select("variable", ["b"]))
        with pytest.raises(ValueError):
            result = self.API.retrieve(request)
            result.pprint()

    def test_unsliceable_axis_in_a_shape(self):
        request = Request(Box(["level", "variable"], [10, "a"], [11, "a"]), Select("date", ["2000-01-01"]))
        with pytest.raises(UnsliceableShapeError):
            result = self.API.retrieve(request)
            result.pprint()
