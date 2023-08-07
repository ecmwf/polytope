import numpy as np
import pandas as pd
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129, 11),
            dims=("date", "step", "level", "long"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "long": [-0.1, -0.2, -0.3, -0.4, -0.5, -0.6, -0.7, -0.8, -0.9, -1.0, -1.1],
            },
        )
        options = {
            "long": {"transformation": {"cyclic": [-1.1, -0.1]}},
            "level": {"transformation": {"cyclic": [1, 129]}},
        }
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    # Testing different shapes

    def test_cyclic_float_axis_across_seam(self):
        request = Request(
            Box(["step", "long"], [0, 0.8], [3, 1.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 20
        assert [leaf.value for leaf in result.leaves] == [
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
        ]

    def test_cyclic_float_axis_inside_cyclic_range(self):
        request = Request(
            Box(["step", "long"], [0, 0.0], [3, 0.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 16
        assert [leaf.value for leaf in result.leaves] == [
            0.0,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.0,
            0.1,
            0.2,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
        ]

    def test_cyclic_float_axis_above_axis_range(self):
        request = Request(
            Box(["step", "long"], [0, 1.3], [3, 1.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 10
        assert [leaf.value for leaf in result.leaves] == [1.3, 1.4, 1.5, 1.6, 1.7, 1.3, 1.4, 1.5, 1.6, 1.7]

    def test_cyclic_float_axis_two_range_loops(self):
        request = Request(
            Box(["step", "long"], [0, 0.3], [3, 2.7]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 50
        assert [leaf.value for leaf in result.leaves] == [
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
            0.3,
            0.4,
            0.5,
            0.6,
            0.7,
            0.8,
            0.9,
            1.0,
            1.1,
            1.2,
            1.3,
            1.4,
            1.5,
            1.6,
            1.7,
            1.8,
            1.9,
            2.0,
            2.1,
            2.2,
            2.3,
            2.4,
            2.5,
            2.6,
            2.7,
        ]

    def test_cyclic_float_axis_below_axis_range(self):
        request = Request(
            Box(["step", "long"], [0, -0.7], [3, -0.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 10
        assert [leaf.value for leaf in result.leaves] == [-0.7, -0.6, -0.5, -0.4, -0.3, -0.7, -0.6, -0.5, -0.4, -0.3]

    def test_cyclic_float_axis_below_axis_range_crossing_seam(self):
        request = Request(
            Box(["step", "long"], [0, -0.7], [3, 0.3]), Select("date", ["2000-01-01"]), Select("level", [128])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 22
        assert [leaf.value for leaf in result.leaves] == [
            -0.7,
            -0.6,
            -0.5,
            -0.4,
            -0.3,
            -0.2,
            -0.1,
            0.0,
            0.1,
            0.2,
            0.3,
            -0.7,
            -0.6,
            -0.5,
            -0.4,
            -0.3,
            -0.2,
            -0.1,
            0.0,
            0.1,
            0.2,
            0.3,
        ]
