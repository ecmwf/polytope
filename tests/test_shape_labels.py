import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


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
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        options = {"compressed_axes_config": ["date", "step", "level"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    # Testing different shapes

    def test_2D_box(self):
        request = Request(
            Box(["step", "level"], [3, 10], [6, 11], label="box1"), Select("date", ["2000-01-01"], label="select1")
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert result.leaves[0].labels == ["box1"]
        assert result.leaves[0].parent.labels == ["box1"]
        assert result.leaves[0].parent.parent.labels == ["select1"]
