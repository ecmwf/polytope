import pandas as pd
import pytest
import numpy as np

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select
import xarray as xr
import geopandas as gpd
import matplotlib.pyplot as plt

from helper_functions import download_test_data, find_nearest_latlon


class TestQuadTreeSlicer:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        self.slicer = HullSlicer()
        self.engine_options = {
            "step": "hullslicer",
            "time": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
            "oceanModelLayer": "hullslicer",
            "valid_time": "hullslicer",
        }
        arr = xr.open_dataset("../../Downloads/Reference_eORCA12_U_to_HEALPix_32.grib", engine='cfgrib').avg_uo
        self.latitudes = arr.latitude.values
        self.longitudes = arr.longitude.values
        self.points = list(zip(self.latitudes, self.longitudes))
        self.options = {
            "values": {"mapper": {"type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            # "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            # "step": {"type_change": "int"},
            # "number": {"type_change": "int"},
        }
        # self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"}
        # self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options, point_cloud_options=self.points)
        self.API = Polytope(
            datacube=arr,
            engine=self.slicer,
            axis_options=self.options,
            engine_options=self.engine_options,
            point_cloud_options=self.points,
        )

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        request = Request(
            Select("step", [np.timedelta64(0, "ns")]),
            Select("oceanModelLayer", [65.0]),
            Select("time", [pd.Timestamp("2017-09-06T00:00:00.000000000")]),
            Select("valid_time", [pd.Timestamp("2017-09-06T00:00:00.000000000")]),
            Box(["latitude", "longitude"], [65, 270], [75, 300]),
        )
        import time
        time0 = time.time()
        result = self.API.retrieve(request)
        time1 = time.time()
        print("TIME TAKEN TO EXTRACT")
        print(time1 - time0)
        result.pprint()

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            lon = cubepath["longitude"] - 360
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

        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)

        plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        plt.colorbar(label="Temperature")
        plt.show()

        
