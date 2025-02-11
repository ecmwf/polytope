# from helper_functions import find_nearest_latlon
import time

# import geopandas as gpd
# import matplotlib.pyplot as plt
import numpy as np

# import pandas as pd
import pytest

# from earthkit import data
import xarray as xr

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.engine_options = {
            "deptht": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
        }

        ds = xr.open_dataset("../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.nc", engine="netcdf4")
        self.arr = ds.votemper

        self.latitudes = self.arr.coords["nav_lat"].values
        lats = []
        for lat in self.latitudes:
            lats.extend(lat)
        self.latitudes = lats
        self.longitudes = self.arr.nav_lon.values
        lons = []
        for lon in self.longitudes:
            lons.extend(lon)
        self.longitudes = lons

        # # Drop the x and y dimensions
        nav_lat_flat = self.arr.nav_lat.values.ravel()
        deptht_flat = self.arr.deptht.values.ravel()
        interm_data = self.arr.data[0]
        new_interm_data = []
        for data in interm_data:
            new_data = data.ravel()
            new_interm_data.append(new_data)

        # Create a new dimension, for example, "grid_index"
        grid_index = np.arange(nav_lat_flat.size)

        self.arr = xr.DataArray(
            new_interm_data,
            dims=("deptht", "values"),
            coords={
                "deptht": deptht_flat,
                "values": grid_index,
            },
        )

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
            Select("deptht", [0.5058], method="nearest"),
            Box(["latitude", "longitude"], [-55, 50], [-50, 55]),
        )

        self.API = Polytope(
            datacube=self.arr,
            options=self.options,
            engine_options=self.engine_options,
            point_cloud_options=self.points,
        )

        time0 = time.time()
        result = self.API.retrieve(request)
        time1 = time.time()
        print("TIME TAKEN TO EXTRACT")
        print(time1 - time0)
        assert len(result.leaves) == 1386
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
        #     # nearest_points = find_nearest_latlon("../../Downloads/votemper_ORAS5_1m_197902_grid_T_02.grib2", lat,
        #                                             lon)
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
