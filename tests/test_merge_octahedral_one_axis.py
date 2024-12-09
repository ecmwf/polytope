import pytest
from earthkit import data
from helper_functions import download_test_data

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingMultipleTransformationsOneAxis:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
        download_test_data(nexus_url, "foo.grib")

        ds = data.from_source("file", "./tests/data/foo.grib")
        self.latlon_array = ds.to_xarray(engine="cfgrib").isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        self.latlon_array = self.latlon_array.t2m
        self.options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "compressed_axes_config": ["longitude", "latitude", "surface", "step", "time", "valid_time", "number"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.latlon_array,
            engine=self.slicer,
            options=self.options,
        )

    @pytest.mark.internet
    def test_merge_axis(self):
        request = Request(
            Select("number", [0]),
            Select("time", ["2023-06-25T12:00:00"]),
            Select("step", ["00:00:00"]),
            Select("surface", [0]),
            Select("valid_time", ["2023-06-25T12:00:00"]),
            Box(["latitude", "longitude"], [0, 359.8], [0.2, 361.2]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert max(result.leaves[-1].flatten()["longitude"]) == 360.0
        assert min(result.leaves[0].flatten()["longitude"]) == 0.070093457944
