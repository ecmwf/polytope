import pytest
from earthkit import data
from helper_functions import download_test_data

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingMultipleTransformationsOneAxis:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
        download_test_data(nexus_url, "foo.grib")

        ds = data.from_source("file", "./tests/data/foo.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        self.latlon_array = self.latlon_array.t2m
        self.options = {"config": [{"axis_name": "values", "transformations": [{"name": "mapper",
                                                                                "type": "octahedral",
                                                                                "resolution": 1280,
                                                                                "axes": ["latitude", "longitude"]}]},
                                   {"axis_name": "latitude", "transformations": [{"name": "reverse",
                                                                                  "is_reverse": True}]},
                                   {"axis_name": "longitude", "transformations": [{"name": "cyclic",
                                                                                   "range": [0, 360]}]}]}
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.latlon_array, engine=self.slicer, axis_options=self.options)

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
        # result.pprint()
        assert result.leaves[-1].flatten()["longitude"] == 360.0
        assert result.leaves[0].flatten()["longitude"] == 0.070093457944
