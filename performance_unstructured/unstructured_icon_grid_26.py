# Always do performance on data stored on the FDB

import math
import time

import pandas as pd
import pygribjump as gj
import xarray as xr

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select, Polygon, ConvexPolytope

import os
os.environ["FDB_HOME"] = "/Users/male/git/fdb-new-home"

# slicer_type = "quadtree"
file_name = "../../Downloads/icon_grid_0026_R03B07_G.nc"


def get_engine_options(slicer_type):
    engine_options = {
        "step": "hullslicer",
        "date": "hullslicer",
        "levtype": "hullslicer",
        "param": "hullslicer",
        "latitude": slicer_type,
        "longitude": slicer_type,
    }
    return engine_options


def get_grid_points(file_name):
    grid = xr.open_dataset(file_name, engine="netcdf4")

    longitudes = grid.clon.values * 180/math.pi
    latitudes = grid.clat.values * 180/math.pi

    points = list(zip(latitudes, longitudes))
    return points


def set_up_slicing(slicer_type, file_name):
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
                    {"name": "mapper", "type": "irregular", "resolution": 0, "axes": [
                        "latitude", "longitude"], "md5_hash": "f68071a8ac9bae4e965822afb963c04f"}
                ],
            },
        ],
        "pre_path": {"date": "20250110"},
    }

    fdbdatacube = gj.GribJump()

    engine_options = get_engine_options(slicer_type)
    points = get_grid_points(file_name)

    API = Polytope(
        datacube=fdbdatacube,
        options=options,
        engine_options=engine_options,
        point_cloud_options=points,
    )

    return API


# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     Polygon(["latitude", "longitude"], [[0, 0], [0, 10], [10, 10], [10, 0]]),
# )


request = Request(
    Select("date", [pd.Timestamp("20250110T0000")]),
    Select("step", [0]),
    Select("param", ["167"]),
    Select("levtype", ["sfc"]),
    Polygon(["latitude", "longitude"], [[0, 0], [0, 20], [20, 20], [20, 0]]),
)

# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     Polygon(["latitude", "longitude"], [[0, 0], [0, 15], [15, 15], [15, 0]]),
# )

# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     Polygon(["latitude", "longitude"], [[0, 0], [0, 5], [5, 5], [5, 0]]),
# )


# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     ConvexPolytope(["latitude", "longitude"], [[0, 0], [0, 10], [10, 10], [10, 0]]),
# )


print("\n\n")
print("##################################################")
print("TIMES USING QUADTREE SLICER \n\n")
print("##################################################")


API = set_up_slicing("quadtree", file_name)

time0 = time.time()
result = API.retrieve(request)
time1 = time.time()

print("TIME TAKEN TO EXTRACT")
print(time1 - time0)
print(len(result.leaves))


print("\n\n")
print("##################################################")
print("TIMES USING POINT IN POLYGON SLICER \n\n")
print("##################################################")


API = set_up_slicing("point_in_polygon", file_name)

time0 = time.time()
result = API.retrieve(request)
time1 = time.time()

print("TIME TAKEN TO EXTRACT")
print(time1 - time0)
print(len(result.leaves))


print("\n\n")
print("##################################################")
print("TIMES USING OPTIMISED POINT IN POLYGON SLICER \n\n")
print("##################################################")


API = set_up_slicing("optimised_point_in_polygon", file_name)

time0 = time.time()
result = API.retrieve(request)
time1 = time.time()

print("TIME TAKEN TO EXTRACT")
print(time1 - time0)
print(len(result.leaves))
