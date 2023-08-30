import numpy as np
import pandas as pd
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select


class TestMergeTransformation:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(1, 1),
            dims=("date", "time"),
            coords={
                "date": ["2000-01-01"],
                "time": ["06:00"],
            },
        )
        options = {"date": {"transformation": {"merge": {"with": "time", "linkers": [" ", ":00"]}}}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    def test_merge_axis(self):
        request = Request(Select("date", [pd.Timestamp("2000-01-01T06:00:00")]))
        result = self.API.retrieve(request)
        # assert result.leaves[0].flatten()["date"] == np.datetime64("2000-01-01T06:00:00")
        assert result.leaves[0].flatten()["date"] == pd.Timestamp("2000-01-01T06:00:00")
