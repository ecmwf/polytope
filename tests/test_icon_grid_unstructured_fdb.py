import math

# import os
import time

# import geopandas as gpd
# import matplotlib.pyplot as plt
import pandas as pd
import pytest
import xarray as xr
from earthkit import data

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select

# from helper_functions import find_nearest_latlon


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

        ds = data.from_source("file", "../../Downloads/icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2")
        grid = xr.open_dataset("../../Downloads/icon_grid_0026_R03B07_G.nc", engine="netcdf4")

        self.arr = ds.to_xarray(engine="cfgrib").t2m
        self.longitudes = grid.clon.values * 180 / math.pi
        self.latitudes = grid.clat.values * 180 / math.pi
        self.points = list(zip(self.latitudes, self.longitudes))
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
                            "md5_hash": "f68071a8ac9bae4e965822afb963c04f",
                        }
                    ],
                },
            ],
            "pre_path": {"date": "20250110"},
        }

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        import pygribjump as gj

        request = Request(
            Select("date", [pd.Timestamp("20250110T0000")]),
            Select("step", [0]),
            Select("param", ["167"]),
            Select("levtype", ["sfc"]),
            Box(["latitude", "longitude"], [0, 0], [10, 10]),
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
        time1 = time.time()
        assert len(result.leaves) == 1
        print("TIME TAKEN TO EXTRACT")
        print(time1 - time0)
        result.pprint()

        # lats = []
        # lons = []
        # eccodes_lats = []
        # eccodes_lons = []
        # # tol = 1e-8
        # leaves = result.leaves
        # for i in range(len(leaves)):
        #     cubepath = leaves[i].flatten()
        #     lat = cubepath["latitude"][0]
        #     lon = cubepath["longitude"][0]
        #     lats.append(lat)
        #     lons.append(lon)

        #     # # each variable in the netcdf file is a cube
        #     # # cubes = iris.load('../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.nc')
        #     # # iris.save(cubes, '../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.grib2')
        #     # nearest_points = find_nearest_latlon(
        #     #     "../../Downloads/icon-d2_germany_icosahedral_single-level_2025011000_024_2d_t_2m.grib2", lat, lon)
        #     # eccodes_lat = nearest_points[0][0]["lat"]
        #     # eccodes_lon = nearest_points[0][0]["lon"] - 360
        #     # eccodes_lats.append(eccodes_lat)
        #     # eccodes_lons.append(eccodes_lon)
        #     # assert eccodes_lat - tol <= lat
        #     # assert lat <= eccodes_lat + tol
        #     # assert eccodes_lon - tol <= lon
        #     # assert lon <= eccodes_lon + tol

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        # plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        # plt.colorbar(label="Temperature")
        # plt.show()
