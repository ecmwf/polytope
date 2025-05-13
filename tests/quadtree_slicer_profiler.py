import cProfile
import datetime
import math

# import iris
import os
import time

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pygribjump as gj
import pytest
import xarray as xr
from earthkit import data
from helper_functions import find_nearest_latlon

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Point, Polygon, Select

# os.environ["FDB_HOME"] = "/Users/male/git/fdb-new-home"


engine_options = {
    "step": "hullslicer",
    "date": "hullslicer",
    "levtype": "hullslicer",
    "param": "hullslicer",
    "latitude": "quadtree",
    "longitude": "quadtree",
}
print("SETTING UP THE XARRAY")
time_now = time.time()

ds = data.from_source("file", "../../Downloads/icon_global_icosahedral_single-level_2025011000_000_T_2M.grib2")

grid = xr.open_dataset("../../Downloads/icon_grid_0026_R03B07_G.nc", engine="netcdf4")

print(time.time() - time_now)
arr = ds.to_xarray(engine="cfgrib").t2m

longitudes = grid.clon.values * 180 / math.pi
latitudes = grid.clat.values * 180 / math.pi

points = list(zip(latitudes, longitudes))
print("FINISH SETTING UP POINTS")
options = {
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


tri_side = 80
triangle = Polygon(["latitude", "longitude"], [[0, tri_side], [0, 0], [tri_side, 0]])

request = Request(
    # Select("deptht", [0.5058], method="nearest"),
    Select("date", [pd.Timestamp("20250110T0000")]),
    # Select("heightAboveGround", [2.0]),
    # Select("step", [datetime.timedelta(days=0)]),
    Select("step", [0]),
    Select("param", ["167"]),
    Select("levtype", ["sfc"]),
    # Select("time_counter", [pd.Timestamp("1979-02-15")]),
    # Box(["latitude", "longitude"], [0, 0], [5, 5]),
    Box(["latitude", "longitude"], [0, 0], [80, 80]),
)

fdbdatacube = gj.GribJump()

API = Polytope(
    datacube=fdbdatacube,
    options=options,
    engine_options=engine_options,
    point_cloud_options=points,
)

time0 = time.time()
# result = API.retrieve(request)
# time1 = time.time()
# print("TIME TAKEN TO EXTRACT")
# print(time1 - time0)
# print(len(result.leaves))

cProfile.runctx("API.retrieve(request)", globals(), locals(), "profiled_extract_quadtree.pstats")
