import pandas as pd
import pytest
from earthkit import data
from helper_functions import download_test_data, find_nearest_latlon

from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix_nested import (
    NestedHealpixGridMapper,
)
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestHealpixNestedGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/healpix_nested.grib"
        download_test_data(nexus_url, "healpix_nested.grib")

        ds = data.from_source("file", "./tests/data/healpix_nested.grib")[3]
        self.latlon_array = ds.to_xarray(engine="cfgrib").isel(step=0).isel(time=0).isel(heightAboveGround=0).t2m
        self.options = {
            "axis_config": [
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "healpix_nested",
                            "resolution": 128,
                            "axes": ["latitude", "longitude"],
                        }
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "d1", "expver": "0001", "levtype": "sfc", "stream": "clte"},
            "compressed_axes_config": [
                "longitude",
                "latitude",
            ],
            "alternative_axes": [
                {
                    "axis_name": "class",
                    "values": [
                        "d1",
                    ],
                },
                {
                    "axis_name": "activity",
                    "values": [
                        "ScenarioMIP",
                    ],
                },
                {
                    "axis_name": "dataset",
                    "values": ["climate-dt"],
                },
                {
                    "axis_name": "date",
                    "values": ["20200102"],
                },
                {
                    "axis_name": "time",
                    "values": ["0100"],
                },
                {
                    "axis_name": "experiment",
                    "values": ["SSP3-7.0"],
                },
                {
                    "axis_name": "expver",
                    "values": ["0001"],
                },
                {
                    "axis_name": "generation",
                    "values": ["1"],
                },
                {
                    "axis_name": "levtype",
                    "values": ["sfc"],
                },
                {
                    "axis_name": "model",
                    "values": ["IFS-NEMO"],
                },
                {
                    "axis_name": "param",
                    "values": ["167"],
                },
                {
                    "axis_name": "realization",
                    "values": ["1"],
                },
                {
                    "axis_name": "resolution",
                    "values": ["standard"],
                },
                {
                    "axis_name": "stream",
                    "values": ["clte"],
                },
                {
                    "axis_name": "type",
                    "values": ["fc"],
                },
            ],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.latlon_array,
            engine=self.slicer,
            options=self.options,
        )

    @pytest.mark.internet
    def test_healpix_nested_grid_equator(self):
        request = Request(
            Select("valid_time", [pd.Timestamp("20200102T010000")]),
            Select("time", [pd.Timestamp("20200102T010000")]),
            Select("step", [0]),
            Select("heightAboveGround", [2]),
            Box(["latitude", "longitude"], [0, 0], [2, 2]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 7
        tot_leaves = 0
        for leaf in result.leaves:
            tot_leaves += len(leaf.result[1])
        assert tot_leaves == 21

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves[:]):
            cubepath = leaf.flatten()
            lat = cubepath["latitude"]
            lons_ = cubepath["longitude"]
            for i, lon in enumerate(lons_):
                lon = [
                    lon,
                ]
                lats.append(lat)
                lons.append(lon)
                nearest_points = find_nearest_latlon("./tests/data/healpix_nested.grib", lat[0], lon[0])
                eccodes_lat = nearest_points[0][0]["lat"]
                eccodes_lon = nearest_points[0][0]["lon"]
                eccodes_result = nearest_points[3][0]["value"]
                eccodes_lats.append(eccodes_lat)
                eccodes_lons.append(eccodes_lon)

                mapper = NestedHealpixGridMapper("values", ["latitude", "longitude"], 128)
                assert nearest_points[0][0]["index"] == mapper.unmap(lat, lon)[0]
                assert eccodes_lat - tol <= lat[0]
                assert lat[0] <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon[0]
                assert lon[0] <= eccodes_lon + tol
                assert leaf.result[1][i] - 1e-4 <= eccodes_result <= leaf.result[1][i] + 1e-4
        assert len(eccodes_lats) == 21

    @pytest.mark.internet
    def test_healpix_nested_grid_south_pole(self):
        request = Request(
            Select("valid_time", [pd.Timestamp("20200102T010000")]),
            Select("time", [pd.Timestamp("20200102T010000")]),
            Select("step", [0]),
            Select("heightAboveGround", [2]),
            Box(["latitude", "longitude"], [-87, 0], [-85, 10]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 5
        tot_leaves = 0
        for leaf in result.leaves:
            tot_leaves += len(leaf.result[1])
        assert tot_leaves == 5

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves[:]):
            cubepath = leaf.flatten()
            lat = cubepath["latitude"]
            lons_ = cubepath["longitude"]
            for i, lon in enumerate(lons_):
                lon = [
                    lon,
                ]
                lats.append(lat)
                lons.append(lon)
                nearest_points = find_nearest_latlon("./tests/data/healpix_nested.grib", lat[0], lon[0])
                eccodes_lat = nearest_points[0][0]["lat"]
                eccodes_lon = nearest_points[0][0]["lon"]
                eccodes_result = nearest_points[3][0]["value"]
                eccodes_lats.append(eccodes_lat)
                eccodes_lons.append(eccodes_lon)

                mapper = NestedHealpixGridMapper("values", ["latitude", "longitude"], 128)
                assert nearest_points[0][0]["index"] == mapper.unmap(lat, lon)[0]
                assert eccodes_lat - tol <= lat[0]
                assert lat[0] <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon[0]
                assert lon[0] <= eccodes_lon + tol
                assert leaf.result[1][i] - 1e-4 <= eccodes_result <= leaf.result[1][i] + 1e-4
        assert len(eccodes_lats) == 5

    @pytest.mark.internet
    def test_healpix_nested_grid_north_pole(self):
        request = Request(
            Select("valid_time", [pd.Timestamp("20200102T010000")]),
            Select("time", [pd.Timestamp("20200102T010000")]),
            Select("step", [0]),
            Select("heightAboveGround", [2]),
            Box(["latitude", "longitude"], [83, 0], [86, 10]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 9
        tot_leaves = 0
        for leaf in result.leaves:
            tot_leaves += len(leaf.result[1])
        assert tot_leaves == 15

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves[:]):
            cubepath = leaf.flatten()
            lat = cubepath["latitude"]
            lons_ = cubepath["longitude"]
            for i, lon in enumerate(lons_):
                lon = [
                    lon,
                ]
                lats.append(lat)
                lons.append(lon)
                nearest_points = find_nearest_latlon("./tests/data/healpix_nested.grib", lat[0], lon[0])
                eccodes_lat = nearest_points[0][0]["lat"]
                eccodes_lon = nearest_points[0][0]["lon"]
                eccodes_result = nearest_points[3][0]["value"]
                eccodes_lats.append(eccodes_lat)
                eccodes_lons.append(eccodes_lon)

                mapper = NestedHealpixGridMapper("values", ["latitude", "longitude"], 128)
                assert nearest_points[0][0]["index"] == mapper.unmap(lat, lon)[0]
                assert eccodes_lat - tol <= lat[0]
                assert lat[0] <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon[0]
                assert lon[0] <= eccodes_lon + tol
                assert leaf.result[1][i] - 1e-4 <= eccodes_result <= leaf.result[1][i] + 1e-4
        assert len(eccodes_lats) == 15
