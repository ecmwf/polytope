import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select
from polytope_feature.utility.exceptions import UnsliceableShapeError


class TestSlicingUnsliceableAxis:
    def setup_method(self, method):
        # create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 1, 129),
            dims=("date", "variable", "level"),
            coords={"date": pd.date_range("2000-01-01", "2000-01-03", 3), "variable": ["a"], "level": range(1, 130)},
        )
        self.slicer = HullSlicer()
        options = {"compressed_axes_config": ["date", "variable", "level"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    # Testing different shapes

    def test_finding_existing_variable(self):
        request = Request(Box(["level"], [10], [11]), Select("date", ["2000-01-01"]), Select("variable", ["a"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_finding_nonexisting_variable(self):
        request = Request(Box(["level"], [10], [11]), Select("date", ["2000-01-01"]), Select("variable", ["b"]))
        with pytest.raises(ValueError):
            result = self.API.retrieve(request)
            result.pprint()

    def test_unsliceable_axis_in_a_shape(self):
        # does it work when we ask a box or disk of an unsliceable axis?
        request = Request(Box(["level", "variable"], [10, "a"], [11, "a"]), Select("date", ["2000-01-01"]))
        with pytest.raises(UnsliceableShapeError):
            result = self.API.retrieve(request)
            result.pprint()
