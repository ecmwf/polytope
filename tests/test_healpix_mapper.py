import pytest
from earthkit import data
from helper_functions import download_test_data, find_nearest_latlon

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestOctahedralGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/healpix.grib"
        download_test_data(nexus_url, "healpix.grib")

        ds = data.from_source("file", "./tests/data/healpix.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(time=0).isel(isobaricInhPa=0).z
        self.options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "healpix", "resolution": 32, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            ],
            "compressed_axes_config": ["longitude", "latitude", "step", "time", "isobaricInhPa", "valid_time"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            request={},
            datacube=self.latlon_array,
            engine=self.slicer,
            options=self.options,
        )

    @pytest.mark.internet
    def test_healpix_grid(self):
        request = Request(
            Box(["latitude", "longitude"], [-2, -2], [10, 10]),
            Select("time", ["2022-12-14T12:00:00"]),
            Select("step", ["01:00:00"]),
            Select("isobaricInhPa", [500]),
            Select("valid_time", ["2022-12-14T13:00:00"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 40

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves):
            cubepath = leaf.flatten()
            tree_result = leaf.result[1].tolist()
            lat = cubepath["latitude"][0]
            new_lons = cubepath["longitude"]
            for lon in new_lons:
                lats.append(lat)
                lons.append(lon)
                nearest_points = find_nearest_latlon("./tests/data/healpix.grib", lat, lon)
                eccodes_lat = nearest_points[0][0]["lat"]
                eccodes_lon = nearest_points[0][0]["lon"]
                eccodes_result = nearest_points[0][0]["value"]
                assert eccodes_lat - tol <= lat
                assert lat <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon
                assert lon <= eccodes_lon + tol
                assert eccodes_result == tree_result
            eccodes_lats.append(lat)
        assert len(eccodes_lats) == 40
