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


# TODO: here, compute circles with the same bounding box as the boxes to compare?

def find_circle_points(num_points, centre, radius):

    expanded_radius = _expansion_to_circumscribe_circle(num_points)
    points = _points_on_circle(num_points, expanded_radius)

    for i in range(0, len(points)):
        x = centre[0] + points[i][0] * radius[0]
        y = centre[1] + points[i][1] * radius[1]
        points[i] = [x, y]
    return points


def _points_on_circle(n, r):
    return [[math.cos(2 * math.pi / n * x) * r, math.sin(2 * math.pi / n * x) * r] for x in range(0, n)]


def _expansion_to_circumscribe_circle(n):
    half_angle_between_segments = math.pi / n
    return 1 / math.cos(half_angle_between_segments)


num_points = 32

# Disk with bounding box [[0,0], [10,10]]

# center = [6, 6]

# radius = [5, 5]

# points = find_circle_points(num_points, center, radius)

# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     ConvexPolytope(["latitude", "longitude"], points),
# )


# Disk with bounding box [[0,0], [15,15]]

# center = [8.5, 8.5]

# radius = [7.5, 7.5]

# points = find_circle_points(num_points, center, radius)

# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     ConvexPolytope(["latitude", "longitude"], points),
# )


# Disk with bounding box [[0,0], [20,20]]

center = [11, 11]

radius = [10, 10]

points = find_circle_points(num_points, center, radius)

request = Request(
    Select("date", [pd.Timestamp("20250110T0000")]),
    Select("step", [0]),
    Select("param", ["167"]),
    Select("levtype", ["sfc"]),
    ConvexPolytope(["latitude", "longitude"], points),
)


# Disk with bounding box [[0,0], [5,5]]

# center = [3.5, 3.5]

# radius = [2.5, 2.5]

# points = find_circle_points(num_points, center, radius)

# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     ConvexPolytope(["latitude", "longitude"], points),
# )


# Disk with bounding box [[0,0], [5,5]] but in many polygons

# center = [3.5, 3.5]

# radius = [2.5, 2.5]

# points = find_circle_points(num_points, center, radius)

# request = Request(
#     Select("date", [pd.Timestamp("20250110T0000")]),
#     Select("step", [0]),
#     Select("param", ["167"]),
#     Select("levtype", ["sfc"]),
#     Polygon(["latitude", "longitude"], points),
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
