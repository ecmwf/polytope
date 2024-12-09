import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingCyclicAxisNotOverZero:
    def setup_method(self, method):
        # create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129, 11),
            dims=("date", "step", "level", "long"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "long": [-0.1, -0.2, -0.3, -0.4, -0.5, -0.6, -0.7, -0.8, -0.9, -1.0, -1.1][::-1],
            },
        )
        self.options = {
            "axis_config": [
                {"axis_name": "long", "transformations": [{"name": "cyclic", "range": [-1.1, -0.1]}]},
                {"axis_name": "level", "transformations": [{"name": "cyclic", "range": [1, 129]}]},
            ],
            "compressed_axes_config": ["long", "level", "step", "date"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=array,
            engine=self.slicer,
            options=self.options,
        )

    # Testing different shapes

    def test_cyclic_float_axis_across_seam(self):
        request = Request(
            Box(["step", "long"], [0, 0.8], [3, 1.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (-1.1,),
            (-1.0,),
            (-0.9,),
            (-0.8,),
            (-0.7,),
            (-0.6,),
            (-0.5,),
            (-0.4,),
            (-0.3,),
            (-0.2,),
        ]

    def test_cyclic_float_axis_inside_cyclic_range(self):
        request = Request(
            Box(["step", "long"], [0, 0.0], [3, 0.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (-1.0,),
            (-0.9,),
            (-0.8,),
            (-0.7,),
            (-0.6,),
            (-0.5,),
            (-0.4,),
            (-0.3,),
        ]

    def test_cyclic_float_axis_above_axis_range(self):
        request = Request(
            Box(["step", "long"], [0, 1.3], [3, 1.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (-0.7,),
            (-0.6,),
            (-0.5,),
            (-0.4,),
            (-0.3,),
        ]

    def test_cyclic_float_axis_two_range_loops(self):
        request = Request(
            Box(["step", "long"], [0, 0.3], [3, 2.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (-1.1,),
            (-1.1,),
            (-1.0,),
            (-1.0,),
            (-0.9,),
            (-0.9,),
            (-0.8,),
            (-0.8,),
            (-0.7,),
            (-0.7,),
            (-0.7,),
            (-0.6,),
            (-0.6,),
            (-0.6,),
            (-0.5,),
            (-0.5,),
            (-0.5,),
            (-0.4,),
            (-0.4,),
            (-0.4,),
            (-0.3,),
            (-0.3,),
            (-0.3,),
            (-0.2,),
            (-0.2,),
        ]

    def test_cyclic_float_axis_below_axis_range(self):
        request = Request(
            Box(["step", "long"], [0, -0.7], [3, -0.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (-0.7,),
            (-0.6,),
            (-0.5,),
            (-0.4,),
            (-0.3,),
        ]

    def test_cyclic_float_axis_below_axis_range_crossing_seam(self):
        request = Request(
            Box(["step", "long"], [0, -0.7], [3, 0.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (-1.0,),
            (-0.9,),
            (-0.8,),
            (-0.7,),
            (-0.7,),
            (-0.6,),
            (-0.5,),
            (-0.4,),
            (-0.3,),
            (-0.2,),
            (-0.1,),
        ]
