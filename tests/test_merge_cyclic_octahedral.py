import numpy as np
import pytest
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select, Span


class TestSlicing4DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(1, 1, 2, 3),
            dims=("date", "time", "values", "step"),
            coords={
                "date": ["2000-01-01"],
                "time": ["06:00"],
                "values": [0, 1],
                "step": [0, 1, 2],
            },
        )
        options = {"date": {"transformation": {"merge": {"with": "time", "linkers": ["T", ":00"]}}},
                   "values": {"transformation": {"mapper": {"type": "octahedral",
                                                            "resolution": 1280,
                                                            "axes": ["latitude", "longitude"]}}},
                   "step": {"transformation": {"cyclic": [0, 1]}},
                   }
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    @pytest.mark.skip(reason="Need date time to not be strings")
    def test_merge_axis(self):
        # NOTE: does not work because the date is a string in the merge option...
        request = Request(Select("date", ["2000-01-01T06:00:00"]),
                          Span("step", 0, 3),
                          Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]))
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].flatten()["date"] == "2000-01-01T06:00:00"
