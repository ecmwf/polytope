import pytest
from earthkit import data
from helper_functions import download_test_data, find_nearest_latlon

from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestOctahedralGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
        download_test_data(nexus_url, "foo.grib")

        ds = data.from_source("file", "./tests/data/foo.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
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
            ],
            "compressed_axes_config": ["longitude", "latitude", "number", "step", "time", "surface", "valid_time"],
        }
        self.API = Polytope(
            request={},
            datacube=self.latlon_array,
            options=self.options,
        )

    @pytest.mark.internet
    def test_octahedral_grid(self):
        request = Request(
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
            Select("number", [0]),
            Select("time", ["2023-06-25T12:00:00"]),
            Select("step", ["00:00:00"]),
            Select("surface", [0]),
            Select("valid_time", ["2023-06-25T12:00:00"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 9

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves):
            cubepath = leaf.flatten()
            lat = cubepath["latitude"]
            lon = cubepath["longitude"]
            tree_result = leaf.result[1].tolist()
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("./tests/data/foo.grib", lat[0], lon[0])
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_value = nearest_points[0][0]["value"]
            eccodes_lats.append(eccodes_lat)
            assert eccodes_lat - tol <= lat[0]
            assert lat[0] <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon[0]
            assert lon[0] <= eccodes_lon + tol
            assert eccodes_value == tree_result
        assert len(eccodes_lats) == 9
