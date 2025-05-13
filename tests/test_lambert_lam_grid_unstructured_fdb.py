import csv
import math

# import iris
import os
import time

import numpy as np
import pandas as pd
import pytest
from earthkit import data
from helper_functions import find_nearest_latlon

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select

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
                reader = csv.reader(file, delimiter=" ")
                for row in reader:
                    row = [val for val in row if val]  # Remove empty values (caused by extra spaces)
                    values.append(float(row[0]))
            return values

        self.longitudes = open_vals("tests/data/lambert_lam_longitudes.txt")
        self.latitudes = open_vals("tests/data/lambert_lam_latitudes.txt")

        self.points = list(zip(self.latitudes, self.longitudes))
        print((min(self.latitudes), max(self.latitudes), min(self.longitudes), max(self.longitudes)))
        # print(self.points)
        # print([point for point in self.points if 44 <= point[0] <= 87 and 4 <= point[1] <= 7])
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
                            "type": "lambert_conformal",
                            "resolution": 0,
                            "axes": ["latitude", "longitude"],
                            "md5_hash": "3c528b5fd68ca692a8922cbded813465",  # TODO: change to right md5hash
                            "is_spherical": True,
                            "radius": 6371229,
                            "nv": 0,
                            "nx": 1489,
                            "ny": 1489,
                            "LoVInDegrees": 1.93697,
                            "Dx": 500,
                            "Dy": 500,
                            "latFirstInRadians": ((43.6409 + 2.9710306719721302e-05) / 180) * math.pi,
                            "lonFirstInRadians": ((357.32 - 0.00024761029651987343) / 180) * math.pi,
                            "LoVInRadians": (1.93697 / 180) * math.pi,
                            "Latin1InRadians": (47.082971 / 180) * math.pi,
                            "Latin2InRadians": (47.082971 / 180) * math.pi,
                            "LaDInRadians": (47.082971 / 180) * math.pi,
                        }
                    ],
                },
            ],
            "pre_path": {"date": "20250221"},
        }

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):

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
            # Box(["latitude", "longitude"], [44, 5.5], [44.5, 6.5]),
            Box(["latitude", "longitude"], [44, 5.5], [44.25, 5.55]),
            # triangle,
        )

        self.fdbdatacube = gj.GribJump()

        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options=self.engine_options,
            # point_cloud_options=self.points,
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
        tol = 1e-3
        leaves = result.leaves
        for i in range(len(leaves)):
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0]
            lats.append(lat)
            lons.append(lon)

            # each variable in the netcdf file is a cube
            # cubes = iris.load('../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.nc')
            # iris.save(cubes, '../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.grib2')
            nearest_points = find_nearest_latlon("tests/data/lambert_lam_one_message.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            print("LONGITUDE")
            print(eccodes_lon - lon)
            print("LATITUDE")
            print(eccodes_lat - lat)
            assert lon <= eccodes_lon + tol

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # self.longitudes = [lon-360 if lon > 360 else lon for lon in self.longitudes]
        new_lons = []
        for lon in self.longitudes:
            if lon > 180:
                print("HERE")
                new_lons.append(lon - 360)
            else:
                new_lons.append(lon)
        self.longitudes = new_lons

        self.lons = np.array(self.longitudes)
        self.lats = np.array(self.latitudes)

        # Create boolean masks for each condition
        # lon_mask = (self.lons >= 5.5) & (self.lons <= 6.5)
        # lat_mask = (self.lats >= 44.0) & (self.lats <= 44.5)

        # Combine both masks
        # combined_mask = lon_mask & lat_mask

        # Get indices where both conditions hold
        # indices = np.where(combined_mask)[0]

        # # plt.scatter([lon for lon in self.longitudes if 5.5 <= lon <= 6.5], [
        # #             lat for lat in self.latitudes if 44 <= lat <= 44.5], s=14, color="blue")
        # # plt.scatter(self.lons[combined_mask], self.lats[combined_mask], s=14, color="blue")
        # plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        # plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        # plt.colorbar(label="Temperature")
        # plt.show()
