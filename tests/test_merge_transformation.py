import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Select


class TestMergeTransformation:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        self.array = xr.DataArray(
            np.random.randn(1, 1),
            dims=("date", "time"),
            coords={
                "date": ["20000101"],
                "time": ["0600"],
            },
        )
        self.options = {
            "axis_config": [
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                }
            ],
            "compressed_axes_config": ["date", "time"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.array,
            engine=self.slicer,
            options=self.options,
        )

    def test_merge_axis(self):
        request = Request(Select("date", [pd.Timestamp("20000101T060000")]))
        result = self.API.retrieve(request)
        assert result.leaves[0].flatten()["date"] == (np.datetime64("2000-01-01T06:00:00"),)
