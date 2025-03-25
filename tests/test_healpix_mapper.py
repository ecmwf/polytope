import pytest
from earthkit import data
from helper_functions import download_test_data, find_nearest_latlon

from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix import (
    HealpixGridMapper,
)
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestHealpixGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/healpix.grib"
        download_test_data(nexus_url, "healpix.grib")

        ds = data.from_source("file", "./tests/data/healpix.grib")
        self.latlon_array = ds.to_xarray(engine="cfgrib").isel(step=0).isel(time=0).isel(isobaricInhPa=0).z
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
        assert len(result.leaves) == 10
        assert result.leaves[0].result[1].size == 4
        assert result.leaves[1].result[1].size == 5

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves):
            cubepath = leaf.flatten()
            tree_result = leaf.result[1].tolist()
            lat = cubepath["latitude"][0]
            new_lons = cubepath["longitude"]
            for j, lon in enumerate(new_lons):
                lats.append(lat)
                lons.append(lon)
                nearest_points = find_nearest_latlon("./tests/data/healpix.grib", lat, lon)
                eccodes_lat = nearest_points[0][0]["lat"]
                eccodes_lon = nearest_points[0][0]["lon"]
                eccodes_result = nearest_points[0][0]["value"]

                mapper = HealpixGridMapper("base", ["base1", "base2"], 32)
                assert nearest_points[0][0]["index"] == mapper.unmap((lat,), (lon,))[0]
                assert eccodes_lat - tol <= lat
                assert lat <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon
                assert lon <= eccodes_lon + tol
                tol = 1e-2
                assert abs(eccodes_result - tree_result[j]) <= tol
            eccodes_lats.append(lat)
        assert len(eccodes_lats) == 10
