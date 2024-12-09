import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingCyclic:
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
        self.options = {
            "axis_config": [
                {"axis_name": "long", "transformations": [{"name": "cyclic", "range": [0, 1.0]}]},
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
        assert len(result.leaves) == 1
        result.pprint()
        assert [(val,) for val in result.leaves[0].values] == [
            (0.1,),
            (0.2,),
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
            (0.8,),
            (0.9,),
            (1.0,),
        ]

    def test_cyclic_float_axis_across_seam_repeated(self):
        request = Request(
            Box(["step", "long"], [0, 0.0], [3, 1.0]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.0,),
            (0.1,),
            (0.2,),
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
            (0.8,),
            (0.9,),
            (1.0,),
        ]

    def test_cyclic_float_axis_across_seam_repeated_twice(self):
        request = Request(
            Box(["step", "long"], [0, 0.0], [3, 2.0]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.0,),
            (0.0,),
            (0.1,),
            (0.1,),
            (0.2,),
            (0.2,),
            (0.3,),
            (0.3,),
            (0.4,),
            (0.4,),
            (0.5,),
            (0.5,),
            (0.6,),
            (0.6,),
            (0.7,),
            (0.7,),
            (0.8,),
            (0.8,),
            (0.9,),
            (0.9,),
            (1.0,),
        ]

    def test_cyclic_float_axis_inside_cyclic_range(self):
        request = Request(
            Box(["step", "long"], [0, 0.0], [3, 0.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.0,),
            (0.1,),
            (0.2,),
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
        ]

    def test_cyclic_float_axis_above_axis_range(self):
        request = Request(
            Box(["step", "long"], [0, 1.3], [3, 1.7]),
            Select("date", ["2000-01-01"]),
            Select("level", [128]),
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
        ]

    def test_cyclic_float_axis_two_range_loops(self):
        request = Request(
            Box(["step", "long"], [0, 0.3], [3, 2.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.0,),
            (0.1,),
            (0.1,),
            (0.2,),
            (0.2,),
            (0.3,),
            (0.3,),
            (0.3,),
            (0.4,),
            (0.4,),
            (0.4,),
            (0.5,),
            (0.5,),
            (0.5,),
            (0.6,),
            (0.6,),
            (0.6,),
            (0.7,),
            (0.7,),
            (0.7,),
            (0.8,),
            (0.8,),
            (0.9,),
            (0.9,),
            (1.0,),
        ]

    def test_cyclic_float_axis_below_axis_range(self):
        request = Request(
            Box(["step", "long"], [0, -0.7], [3, -0.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
        ]

    def test_cyclic_float_axis_below_axis_range_crossing_seam(self):
        request = Request(
            Box(["step", "long"], [0, -0.7], [3, 0.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.0,),
            (0.1,),
            (0.2,),
            (0.3,),
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
            (0.8,),
            (0.9,),
        ]

    def test_cyclic_float_axis_reversed(self):
        request = Request(
            Box(["step", "long"], [0, 1.7], [3, 1.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
        ]

    def test_two_cyclic_axis_wrong_axis_order(self):
        request = Request(Box(["step", "long", "level"], [0, 1.3, 131], [3, 1.7, 132]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
        ]

    def test_two_cyclic_axis(self):
        request = Request(Box(["step", "level", "long"], [0, 131, 1.3], [3, 132, 1.7]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [
            (0.3,),
            (0.4,),
            (0.5,),
            (0.6,),
            (0.7,),
        ]

    def test_select_cyclic_float_axis_edge(self):
        request = Request(Box(["step", "level"], [0, 3], [3, 5]), Select("date", ["2000-01-01"]), Select("long", [0]))
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [(0.0,)]

    def test_cyclic_int_axis(self):
        request = Request(Box(["step", "level"], [0, 3], [3, 5]), Select("date", ["2000-01-01"]), Select("long", [0.1]))
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1
        assert [(val,) for val in result.leaves[0].values] == [(0.1,)]
