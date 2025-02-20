import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select, Union


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129),
            dims=("date", "step", "level"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
            },
        )
        self.slicer = HullSlicer()
        options = {"compressed_axes_config": ["level", "step", "date"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_point(self):
        request = Request(Point(["step", "level"], [[3, 10]]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert result.leaves[0].axis.name == "level"

    def test_multiple_points(self):
        # request = Request(Point(["step", "level"], [[3, 10], [3, 12]]), Select("date", ["2000-01-01"]))
        request = Request(
            Union(["step", "level"], Point(["step", "level"], [[3, 10]]), Point(["step", "level"], [[3, 12]])),
            Select("date", ["2000-01-01"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 2
        assert result.leaves[0].axis.name == "level"

    def test_point_surrounding_step(self):
        request = Request(Point(["step", "level"], [[2, 10]], method="surrounding"), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert np.shape(result.leaves[0].result[1]) == (1, 2, 3)

    def test_point_surrounding_exact_step(self):
        request = Request(Point(["step", "level"], [[3, 10]], method="surrounding"), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert np.shape(result.leaves[0].result[1]) == (1, 3, 3)
