# import geopandas as gpd
# import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
from earthkit import data
from helper_functions import find_nearest_latlon

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.engine_options = {
            "step": "hullslicer",
            "time": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
            "oceanModelLayer": "hullslicer",
            "valid_time": "hullslicer",
        }

        ds = data.from_source("file", "../../Downloads/Reference_eORCA12_U_to_HEALPix_32.grib")
        self.arr = ds.to_xarray(engine="cfgrib").avg_uox

        self.latitudes = self.arr.latitude.values
        self.longitudes = self.arr.longitude.values
        self.points = list(zip(self.latitudes, self.longitudes))
        self.options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}
                    ],
                },
            ],
        }

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        request = Request(
            Select("step", [np.timedelta64(0, "ns")]),
            Select("oceanModelLayer", [65.0]),
            Select("time", [pd.Timestamp("2017-09-06T00:00:00.000000000")]),
            Box(["latitude", "longitude"], [65, 270], [75, 300]),
        )

        self.API = Polytope(
            datacube=self.arr,
            options=self.options,
            engine_options=self.engine_options,
            point_cloud_options=self.points,
        )
        import time

        time0 = time.time()
        result = self.API.retrieve(request)
        time1 = time.time()
        print("TIME TAKEN TO EXTRACT")
        print(time1 - time0)
        print(len(result.leaves))
        result.pprint()

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0] - 360
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("../../Downloads/Reference_eORCA12_U_to_HEALPix_32.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"] - 360
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        # plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        # plt.colorbar(label="Temperature")
        # plt.show()
