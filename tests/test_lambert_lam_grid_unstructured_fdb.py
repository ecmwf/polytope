import math

# import iris
import os
import time

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pytest
import xarray as xr
from earthkit import data
from helper_functions import find_nearest_latlon

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Point, Select, Polygon
import csv

os.environ["FDB_HOME"] = "/Users/male/git/fdb-de330-home"


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.engine_options = {
            "step": "hullslicer",
            "date": "hullslicer",
            "levtype": "hullslicer",
            "param": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
        }
        print("SETTING UP THE XARRAY")
        time_now = time.time()

        # TODO: load the data from source into an xarray
        ds = data.from_source("file", "tests/data/lambert_lam_one_message.grib")
        # print(ds.to_xarray(engine="cfgrib"))
        self.arr = ds.to_xarray(engine="cfgrib").t
        print(time.time() - time_now)

        def open_vals(file_name):
            values = []
            with open(file_name, "r") as file:
                reader = csv.reader(file, delimiter=' ')
                for row in reader:
                    row = [val for val in row if val]  # Remove empty values (caused by extra spaces)
                    values.append(float(row[0]))
            return values

        self.longitudes = open_vals("tests/data/lambert_lam_longitudes.txt")
        self.latitudes = open_vals("tests/data/lambert_lam_latitudes.txt")

        self.points = list(zip(self.latitudes, self.longitudes))
        print((min(self.latitudes), max(self.latitudes), min(self.longitudes), max(self.longitudes)))
        print("FINISH SETTING UP POINTS")
        self.options = {
            "axis_config": [
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "irregular",
                            "resolution": 0,
                            "axes": ["latitude", "longitude"],
                            "md5_hash": "3c528b5fd68ca692a8922cbded813465",  # TODO: change to right md5hash
                        }
                    ],
                },
            ],
            "pre_path": {"date": "20250221"},
        }

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        import datetime

        import pygribjump as gj

        # tri_side = 80
        # triangle = Polygon(["latitude", "longitude"], [[0, tri_side], [0, 0], [tri_side, 0]])

        request = Request(
            # Select("deptht", [0.5058], method="nearest"),
            Select("date", [pd.Timestamp("20250221T0000")]),
            # Select("heightAboveGround", [2.0]),
            # Select("step", [datetime.timedelta(days=0)]),
            Select("step", [0]),
            Select("param", ["130"]),
            Select("levtype", ["sfc"]),
            # Select("time_counter", [pd.Timestamp("1979-02-15")]),
            # Box(["latitude", "longitude"], [0, 0], [5, 5]),
            Box(["latitude", "longitude"], [0, 0], [80, 80]),
            # triangle,
        )

        self.fdbdatacube = gj.GribJump()

        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options=self.engine_options,
            point_cloud_options=self.points,
        )

        time0 = time.time()
        result = self.API.retrieve(request)
        # result = self.API.slice(self.API.datacube, request.polytopes())
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
        leaves = result.leaves
        for i in range(len(leaves)):
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0]
            lats.append(lat)
            lons.append(lon)

            # # each variable in the netcdf file is a cube
            # # cubes = iris.load('../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.nc')
            # # iris.save(cubes, '../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.grib2')
            # nearest_points = find_nearest_latlon(
            #     "../../Downloads/icon-d2_germany_icosahedral_single-level_2025011000_024_2d_t_2m.grib2", lat, lon)
            # eccodes_lat = nearest_points[0][0]["lat"]
            # eccodes_lon = nearest_points[0][0]["lon"] - 360
            # eccodes_lats.append(eccodes_lat)
            # eccodes_lons.append(eccodes_lon)
            # assert eccodes_lat - tol <= lat
            # assert lat <= eccodes_lat + tol
            # assert eccodes_lon - tol <= lon
            # assert lon <= eccodes_lon + tol

        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)

        plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        plt.colorbar(label="Temperature")
        plt.show()
