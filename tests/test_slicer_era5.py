import numpy as np
import pytest
from earthkit import data
from helper_functions import download_test_data

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingEra5Data:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")

        ds = data.from_source("file", "./tests/data/era5-levels-members.grib")
        array = ds.to_xarray(engine="cfgrib").isel(step=0).t
        self.slicer = HullSlicer()
        options = {
            "axis_config": [{"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]}],
            "compressed_axes_config": ["number", "time", "latitude", "longitude", "step", "isobaricInhPa"],
        }
        self.API = Polytope(
            datacube=array,
            engine=self.slicer,
            options=options,
        )

    @pytest.mark.internet
    def test_2D_box(self):
        request = Request(
            Box(["number", "isobaricInhPa"], [3, 0.0], [6, 1000.0]),
            Select("time", ["2017-01-02T12:00:00"]),
            Box(["latitude", "longitude"], lower_corner=[0.0, 0.0], upper_corner=[10.0, 30.0]),
            Select("step", [np.timedelta64(0, "s")]),
        )

        result = self.API.retrieve(request)
        result.pprint()

        assert len(result.leaves) == 1
