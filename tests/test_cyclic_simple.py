import numpy as np
import pandas as pd
import xarray as xr

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129, 11),
            dims=("date", "step", "level", "long"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "long": [0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0],
            },
        )
        options = {"long": {"cyclic": [0, 1.0]}, "level": {"cyclic": [1, 129]}}
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    # Testing different shapes

    def test_cyclic_float_axis_across_seam(self):
        request = Request(
            Box(["step", "long"], [0, 0.9], [0, 1.2]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 4
        assert [leaf.value for leaf in result.leaves] == [0.1, 0.2, 0.9, 1.0]

    def test_cyclic_float_surrounding(self):
        request = Request(
            Select("step", [0]),
            Select("long", [1.0], method="surrounding"),
            Select("date", ["2000-01-01"]),
            Select("level", [128]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        for leaf in result.leaves:
            path = leaf.flatten()
            lon_val = path["long"]
            assert lon_val in [0.0, 0.1, 0.9, 1.0]

    def test_cyclic_float_surrounding_below_seam(self):
        request = Request(
            Select("step", [0]),
            Select("long", [0.0], method="surrounding"),
            Select("date", ["2000-01-01"]),
            Select("level", [128]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        for leaf in result.leaves:
            path = leaf.flatten()
            lon_val = path["long"]
            assert lon_val in [0.0, 0.1, 0.9, 1.0]
