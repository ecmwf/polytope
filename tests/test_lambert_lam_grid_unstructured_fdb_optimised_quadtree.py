import csv
import math

import matplotlib.pyplot as plt
import pandas as pd
import pytest
from earthkit import data
from helper_functions import find_nearest_latlon

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Polygon, Select

# import os


# os.environ["FDB_HOME"] = "/Users/male/git/fdb-de330-home"


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.engine_options = {
            "step": "hullslicer",
            "date": "hullslicer",
            "levtype": "hullslicer",
            "param": "hullslicer",
            "latitude": "optimised_quadtree",
            "longitude": "optimised_quadtree",
        }

        ds = data.from_source("file", "tests/data/lambert_lam_one_message.grib")
        self.arr = ds.to_xarray(engine="cfgrib").t

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
        print("HOW MANY POINTS IN GRID")
        print(len(self.points))
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
    @pytest.mark.non_stored_data
    def test_quad_tree_slicer_extract(self):
        import pygribjump as gj

        request = Request(
            Select("date", [pd.Timestamp("20250221T0000")]),
            Select("step", [0]),
            Select("param", ["130"]),
            Select("levtype", ["sfc"]),
            Polygon(["latitude", "longitude"], [[44, 5.5], [44, 5.55], [44.25, 5.55], [44.25, 5.5]]),
        )

        self.fdbdatacube = gj.GribJump()

        import time

        time1 = time.time()

        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options=self.engine_options,
        )

        print("TIME TAKEN TO EXTRACT")
        print(time.time() - time1)

        result = self.API.retrieve(request)
        assert len(result.leaves) == 440
        result.pprint()

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-3
        leaves = result.leaves
        for i in range(10):
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0]
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("tests/data/lambert_lam_one_message.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol

        plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        plt.colorbar(label="Temperature")
        plt.show()
