import pytest
import geopandas as gpd
import matplotlib.pyplot as plt
# from earthkit import data
# from helper_functions import download_test_data, find_nearest_latlon

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select
import pandas as pd
from polytope.datacube.transformations.datacube_mappers.mapper_types.healpix_nested import NestedHealpixGridMapper


class TestHealpixNestedGrid:
    def setup_method(self, method):
        # ds = data.from_source("file", "./tests/data/healpix_nested.grib")
        # ds.to_xarray()
        # self.latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        # self.latlon_array = self.latlon_array.t2m
        # self.options = {
        #     "axis_config": [
        #         {
        #             "axis_name": "values",
        #             "transformations": [
        #                 {"name": "mapper", "type": "healpix_nested", "resolution": 1024, "axes": ["latitude", "longitude"]}
        #             ],
        #         },
        #         {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
        #     ],
        #     "compressed_axes_config": ["longitude", "latitude", "number", "step", "time", "surface", "valid_time"],
        # }
        # self.slicer = HullSlicer()
        # self.API = Polytope(
        #     request={},
        #     datacube=self.latlon_array,
        #     engine=self.slicer,
        #     options=self.options,
        # )
        self.options = {
            "axis_config": [
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "healpix_nested", "resolution": 128, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "d1", "expver": "0001", "levtype": "sfc", "stream": "clte"},
            "compressed_axes-config": [
                "longitude",
                "latitude",
            ],
            "alternative_axes": [
                {
                    "axis_name": "class",
                    "values": ["d1",]
                },
                {
                    "axis_name": "activity",
                    "values": ["ScenarioMIP",]
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

    @pytest.mark.internet
    def test_healpix_nested_grid(self):
        import pygribjump as gj

        request = Request(
            Select("activity", ["ScenarioMIP"]),
            Select("class", ["d1"]),
            Select("dataset", ["climate-dt"]),
            Select("date", [pd.Timestamp("20200102T010000")]),
            Select("experiment", ['SSP3-7.0']),
            Select("expver", ["0001"]),
            Select("generation", ["1"]),
            Select("levtype", ["sfc"]),
            Select("model", ["IFS-NEMO"]),
            Select("param", ["167"]),
            Select("realization", ["1"]),
            Select("resolution", ["standard"]),
            Select("stream", ["clte"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [2, 2]),
        )

        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            request=request,
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        
        result = self.API.retrieve(request)
        result.pprint()
        # assert len(result.leaves) == 18
        assert len(result.leaves) == 21

        from helper_functions import download_test_data, find_nearest_latlon

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i, leaf in enumerate(result.leaves[:]):
            cubepath = leaf.flatten()
            result_tree = leaf.result[0]
            lat = cubepath["latitude"]
            lon = cubepath["longitude"]
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("./tests/data/healpix_nested.grib", lat[0], lon[0])
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_result = nearest_points[3][0]["value"]
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)

            mapper = NestedHealpixGridMapper("base", ["base", "base"], 128)
            assert nearest_points[0][0]["index"] == mapper.unmap(lat, lon)
            assert eccodes_lat - tol <= lat[0]
            assert lat[0] <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon[0]
            assert lon[0] <= eccodes_lon + tol
            assert eccodes_result == result_tree
        assert len(eccodes_lats) == 21

        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)

        plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        plt.colorbar(label="Temperature")
        plt.show()