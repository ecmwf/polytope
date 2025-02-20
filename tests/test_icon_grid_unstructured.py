import math
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
from polytope_feature.shapes import Box, Select

# import iris



class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.engine_options = {
            "step": "hullslicer",
            "time": "hullslicer",
            "heightAboveGround": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
        }
        print("SETTING UP THE XARRAY")
        time_now = time.time()

        # ds = data.from_source(
        #     "file", "../../Downloads/icon-d2_germany_icosahedral_single-level_2025011000_024_2d_t_2m.grib2")

        # grid = xr.open_dataset("../../Downloads/icon_grid_0047_R19B07_L.nc", engine="netcdf4")

        ds = data.from_source("file", "../../Downloads/icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2")

        grid = xr.open_dataset("../../Downloads/icon_grid_0026_R03B07_G.nc", engine="netcdf4")

        print(time.time() - time_now)
        self.arr = ds.to_xarray(engine="cfgrib").t2m

        print(self.arr)
        # print("AND GRID")
        # print(grid.clon.values)
        # print(len(grid.clon))
        self.longitudes = grid.clon.values * 180 / math.pi
        self.latitudes = grid.clat.values * 180 / math.pi
        print(grid)

        # self.arr = ds.votemper

        # self.latitudes = self.arr.latitude.values
        # self.longitudes = self.arr.longitude.values
        # self.latitudes = self.arr.coords["nav_lat"].values
        # lats = []
        # for lat in self.latitudes:
        #     lats.extend(lat)
        # self.latitudes = lats
        # self.longitudes = self.arr.nav_lon.values
        # lons = []
        # for lon in self.longitudes:
        #     lons.extend(lon)
        # self.longitudes = lons

        # # self.arr["nav_lat_flat"] = (("grid_index",), self.arr.nav_lat.values.ravel())
        # # self.arr["nav_lon_flat"] = (("grid_index",), self.arr.nav_lon.values.ravel())

        # # # Drop the x and y dimensions
        # # self.arr = self.arr.drop_dims(["x", "y"])
        # nav_lat_flat = self.arr.nav_lat.values.ravel()
        # nav_lon_flat = self.arr.nav_lon.values.ravel()
        # deptht_flat = self.arr.deptht.values.ravel()
        # interm_data = self.arr.data[0]
        # new_interm_data = []
        # for data_pt in interm_data:
        #     new_data = data_pt.ravel()
        #     new_interm_data.append(new_data)
        # print(len(interm_data))

        # # Create a new dimension, for example, "grid_index"
        # grid_index = np.arange(nav_lat_flat.size)

        # # Add the flattened `nav_lat` and `nav_lon` as variables
        # # self.arr = self.arr.assign_coords(grid_index=("values", grid_index))
        # nav_lat_flat_da = xr.DataArray(nav_lat_flat, dims=["grid_index"], coords={"grid_index": grid_index})
        # nav_lon_flat_da = xr.DataArray(nav_lon_flat, dims=["grid_index"], coords={"grid_index": grid_index})

        # # Drop x and y from the original DataArray
        # # ds_cleaned = self.arr.drop(["x", "y"])

        # # Combine everything into a new Dataset if needed
        # # self.arr = xr.Dataset({
        # #     "original_data": ds_cleaned,
        # #     "nav_lat_flat": nav_lat_flat_da,
        # #     "nav_lon_flat": nav_lon_flat_da,
        # # })

        # self.arr = xr.DataArray(
        #     new_interm_data,
        #     dims=("deptht", "values"),
        #     coords={
        #         "deptht": deptht_flat,
        #         "values": grid_index,
        #     },
        # )

        # print(self.arr)
        # self.arr = self.arr.rename({"y": "lat", "nav_lon": "longitude", "x": "values"})
        self.points = list(zip(self.latitudes, self.longitudes))
        print((min(self.latitudes), max(self.latitudes), min(self.longitudes), max(self.longitudes)))
        print("FINISH SETTING UP POINTS")
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
        import datetime

        request = Request(
            # Select("deptht", [0.5058], method="nearest"),
            Select("time", [pd.Timestamp("2025-01-10")]),
            Select("heightAboveGround", [2.0]),
            Select("step", [datetime.timedelta(days=0)]),
            # Select("time_counter", [pd.Timestamp("1979-02-15")]),
            Box(["latitude", "longitude"], [0, 0], [10, 10]),
        )

        self.API = Polytope(
            datacube=self.arr,
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
