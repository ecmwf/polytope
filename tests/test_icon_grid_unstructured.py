# import matplotlib.pyplot as plt
import pandas as pd
from earthkit import data
from helper_functions import download_test_data

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.engine_options = {
            "step": "hullslicer",
            "time": "hullslicer",
            "heightAboveGround": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
        }

        nexus_url = (
            "https://sites.ecmwf.int/repository/polytope/icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2"
        )
        download_test_data(nexus_url, "icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2")

        ds = data.from_source("file", "tests/data/icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2")

        self.arr = ds.to_xarray(engine="cfgrib").t2m

        nexus_url = "https://sites.ecmwf.int/repository/polytope/icon_lons.txt"
        download_test_data(nexus_url, "icon_lons.txt")
        nexus_url = "https://sites.ecmwf.int/repository/polytope/icon_lats.txt"
        download_test_data(nexus_url, "icon_lats.txt")

        import json

        with open("icon_lons.txt", "r") as f:
            self.longitudes = json.load(f)
        with open("icon_lats.txt", "r") as f:
            self.latitudes = json.load(f)

        self.points = list(zip(self.latitudes, self.longitudes))
        self.options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "unstructured",
                            "axes": ["latitude", "longitude"],
                            "points": self.points,
                        }
                    ],
                },
            ],
        }

    def test_quad_tree_slicer_extract(self):
        import datetime

        request = Request(
            Select("time", [pd.Timestamp("2025-01-10")]),
            Select("heightAboveGround", [2.0]),
            Select("step", [datetime.timedelta(days=0)]),
            Box(["latitude", "longitude"], [0, 0], [1, 1]),
        )

        self.API = Polytope(
            datacube=self.arr,
            options=self.options,
            engine_options=self.engine_options,
        )

        result = self.API.retrieve(request)
        assert len(result.leaves) == 69
        result.pprint()

        lats = []
        lons = []
        # eccodes_lats = []
        # eccodes_lons = []
        # tol = 1e-8
        leaves = result.leaves
        for i in range(len(leaves)):
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0]
            lats.append(lat)
            lons.append(lon)

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

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        # plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        # plt.colorbar(label="Temperature")
        # plt.show()
