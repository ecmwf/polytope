import pytest
from earthkit import data
from helper_functions import download_test_data, find_nearest_latlon

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestOctahedralGrid:
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
            ],
            "compressed_axes_config": ["longitude", "latitude", "number", "step", "time", "surface", "valid_time"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.latlon_array,
            engine=self.slicer,
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
        assert len(result.leaves) == 3
        assert result.leaves[0].result[1].size == 3

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
            nearest_points_2 = find_nearest_latlon("./tests/data/foo.grib", lat[0], lon[1])
            nearest_points_3 = find_nearest_latlon("./tests/data/foo.grib", lat[0], lon[2])
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_value = nearest_points[0][0]["value"]
            eccodes_lat_2 = nearest_points_2[0][0]["lat"]
            eccodes_lon_2 = nearest_points_2[0][0]["lon"]
            eccodes_lat_3 = nearest_points_3[0][0]["lat"]
            eccodes_lon_3 = nearest_points_3[0][0]["lon"]
            eccodes_value_2 = nearest_points_2[0][0]["value"]
            eccodes_value_3 = nearest_points_3[0][0]["value"]
            eccodes_lats.append(eccodes_lat)
            assert eccodes_lat - tol <= lat[0]
            assert lat[0] <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon[0]
            assert lon[0] <= eccodes_lon + tol
            assert [eccodes_value, eccodes_value_2, eccodes_value_3] == tree_result
            assert eccodes_lat_2 - tol <= lat[0]
            assert lat[0] <= eccodes_lat_2 + tol
            assert eccodes_lon_2 - tol <= lon[1]
            assert lon[1] <= eccodes_lon_2 + tol
            assert eccodes_lat_3 - tol <= lat[0]
            assert lat[0] <= eccodes_lat_3 + tol
            assert eccodes_lon_3 - tol <= lon[2]
            assert lon[2] <= eccodes_lon_3 + tol
        assert len(eccodes_lats) == 3
