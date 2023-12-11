import numpy as np
import pytest
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select, Span


class TestMultipleTransformations:
    @classmethod
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        self.array = xr.DataArray(
            np.random.randn(1, 1, 4289589, 3),
            dims=("date", "time", "values", "step"),
            coords={
                "date": ["20000101"],
                "time": ["0600"],
                "values": list(range(4289589)),
                "step": [0, 1, 2],
            },
        )
        self.options = {
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "step": {"cyclic": [0, 2]},
        }
        self.xarraydatacube = XArrayDatacube(self.array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.array, engine=self.slicer, axis_options=self.options)

    @pytest.mark.skip(reason="Datacube not formatted right.")
    def test_merge_axis(self):
        # NOTE: does not work because the date is a string in the merge option...
        date = np.datetime64("2000-01-01T06:00:00")
        request = Request(
            Select("date", [date]), Span("step", 0, 3), Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        )
        result = self.API.retrieve(request)
        assert result.leaves[0].flatten()["date"] == np.datetime64("2000-01-01T06:00:00")
        for leaf in result.leaves:
            assert leaf.flatten()["step"] in [0, 1, 2, 3]
