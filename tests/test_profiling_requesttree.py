import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestProfiling:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 7, 129, 100),
            dims=("date", "step", "level", "lat"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15, 18],
                "level": range(1, 130),
                "lat": np.around(np.arange(0.0, 10.0, 0.1), 15),
            },
        )

        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    # Testing different shapes

    @pytest.mark.skip(reason="For performance tests only.")
    def test_slicing_3D_box(self):
        import cProfile

        pr = cProfile.Profile()
        pr.enable()

        request = Request(Box(["step", "level", "lat"], [3, 10, 5.0], [6, 11, 6.0]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 2 * 2 * 11

        pr.disable()
        pr.print_stats(sort="time")
