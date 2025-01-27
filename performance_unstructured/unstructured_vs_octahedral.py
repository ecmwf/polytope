# Compare octahedral grid treated as an unstructured vs as an iso-latitude grid


import math
import time

import pandas as pd
import pygribjump as gj
import xarray as xr

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select, Polygon, ConvexPolytope

import os

from earthkit import data


import os

import requests
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file


# import logging
# logger = logging.getLogger('')
# logger.setLevel(logging.DEBUG)


class HTTPError(Exception):
    def __init__(self, status_code, message):
        self.status_code = status_code
        self.message = message
        super().__init__(f"HTTPError {status_code}: {message}")


def download_test_data(nexus_url, filename):
    local_directory = "./tests/data"

    if not os.path.exists(local_directory):
        os.makedirs(local_directory)

    # Construct the full path for the local file
    local_file_path = os.path.join(local_directory, filename)

    if not os.path.exists(local_file_path):
        session = requests.Session()
        response = session.get(nexus_url)
        if response.status_code != 200:
            raise HTTPError(response.status_code, "Failed to download data.")
        # Save the downloaded data to the local file
        with open(local_file_path, "wb") as f:
            f.write(response.content)


# from tests.helper_functions import download_test_data
# os.environ["FDB_HOME"] = "/Users/male/git/fdb-new-home"
# slicer_type = "quadtree"
# file_name = "../../Downloads/icon_grid_0026_R03B07_G.nc"
nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
download_test_data(nexus_url, "foo.grib")

file_name = "/Users/male/git/polytope/tests/data/foo.grib"

ds = data.from_source("file", "./tests/data/foo.grib")


def get_engine_options(slicer_type):
    engine_options = {
        "step": "hullslicer",
        "date": "hullslicer",
        "levtype": "hullslicer",
        "param": "hullslicer",
        "class": "hullslicer",
        "domain": "hullslicer",
        "expver": "hullslicer",
        "stream": "hullslicer",
        "type": "hullslicer",
        "latitude": slicer_type,
        "longitude": slicer_type,
    }

    return engine_options


def get_grid_points(file_name):
    # grid = xr.open_dataset(file_name, engine="netcdf4")
    grid = data.from_source("file", file_name).to_xarray()

    longitudes = grid.longitude.values

    # print(longitudes)
    latitudes = grid.latitude.values

    points = list(zip(latitudes, longitudes))
    # print(points)
    return points


def set_up_slicing_unstructured(file_name):
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
                        "latitude", "longitude"], "md5_hash": "158db321ae8e773681eeb40e0a3d350f"}
                ],
            },
            {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
        ],
        "compressed_axes_config": [
            "longitude",
            "latitude",
            "levtype",
            "date",
            "domain",
            "expver",
            "param",
            "class",
            "stream",
            "type",
        ],
        "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "type": "fc", "stream": "oper"},
    }

    fdbdatacube = gj.GribJump()

    engine_options = get_engine_options("quadtree")
    points = get_grid_points(file_name)

    API = Polytope(
        datacube=fdbdatacube,
        options=options,
        engine_options=engine_options,
        point_cloud_options=points,
    )

    return API


def set_up_slicing_structured():
    options = {
        # "axis_config": [
        #     {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        #     {
        #         "axis_name": "date",
        #         "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        #     },
        #     {
        #         "axis_name": "values",
        #         "transformations": [
        #             {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": [
        #                 "latitude", "longitude"]}
        #         ],
        #     },
        # ],
        # "pre_path": {"date": "20250110"},
        "axis_config": [
            {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
            {
                "axis_name": "date",
                "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
            },
            {
                "axis_name": "values",
                "transformations": [
                    {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                ],
            },
            {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
        ],
        "compressed_axes_config": [
            "longitude",
            "latitude",
            "levtype",
            "date",
            "domain",
            "expver",
            "param",
            "class",
            "stream",
            "type",
        ],
        "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "type": "fc", "stream": "oper"},
    }

    fdbdatacube = gj.GribJump()

    engine_options = get_engine_options("hullslicer")

    API = Polytope(
        datacube=fdbdatacube,
        options=options,
        engine_options=engine_options,
    )

    return API


def request(box_size):

    request = Request(
        Select("step", [0]),
        Select("levtype", ["sfc"]),
        Select("date", [pd.Timestamp("20240103T0000")]),
        Select("domain", ["g"]),
        Select("expver", ["0001"]),
        Select("param", ["167"]),
        Select("class", ["od"]),
        Select("stream", ["oper"]),
        Select("type", ["fc"]),
        Box(["latitude", "longitude"], [0, 0], [box_size, box_size]),
        # ConvexPolytope(["latitude", "longitude"], [[0, 0], [0, box_size], [box_size, box_size], [box_size, 0]])
    )

    return request


# Compare boxes of different sizes

# box_size_max = 10

# API_structured = set_up_slicing_structured()
# API_unstructured = set_up_slicing_unstructured(file_name)

# request_ = request(box_size_max)

# time1 = time.time()
# print("\n\n")

# result = API_structured.retrieve(request_)
# print("##################################################")

# print("TIME TO RETRIEVE WITH STRUCTURED SLICER")
# print("##################################################")

# print("TIME TO RETRIEVE")
# print(time.time() - time1)

# print("NUM LEAVES")
# leaves = result.leaves
# print(len(leaves))
# print("NUM FOUND VALUES")
# tot_num = 0
# for leaf in leaves:
#     tot_num += len(leaf.result)
# print(tot_num)

# time2 = time.time()

# print("\n\n")
# result = API_unstructured.retrieve(request_)
# print("##################################################")
# print("TIME TO RETRIEVE WITH UNSTRUCTURED SLICER")
# print("##################################################")
# print("TIME TO RETRIEVE")
# print(time.time() - time2)

# print("NUM LEAVES")
# print(len(result.leaves))


# Compare polygons with n vertices

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


def request_disk(num_sides):

    points_disk = find_circle_points(num_sides, [12, 12], [10, 10])

    request = Request(
        Select("step", [0]),
        Select("levtype", ["sfc"]),
        Select("date", [pd.Timestamp("20240103T0000")]),
        Select("domain", ["g"]),
        Select("expver", ["0001"]),
        Select("param", ["167"]),
        Select("class", ["od"]),
        Select("stream", ["oper"]),
        Select("type", ["fc"]),
        # Box(["latitude", "longitude"], [0, 0], box_size),
        ConvexPolytope(["latitude", "longitude"], points_disk)
    )

    return request


n_sides = 256

API_structured = set_up_slicing_structured()
API_unstructured = set_up_slicing_unstructured(file_name)

request_ = request_disk(n_sides)

time1 = time.time()
print("\n\n")

result = API_structured.retrieve(request_)
print("##################################################")

print("TIME TO RETRIEVE WITH STRUCTURED SLICER")
print("##################################################")

print("TIME TO RETRIEVE")
print(time.time() - time1)

print("NUM LEAVES")
leaves = result.leaves
print(len(leaves))
print("NUM FOUND VALUES")
tot_num = 0
for leaf in leaves:
    tot_num += len(leaf.result)
print(tot_num)
result.pprint()

time2 = time.time()

print("\n\n")
result = API_unstructured.retrieve(request_)
print("##################################################")
print("TIME TO RETRIEVE WITH UNSTRUCTURED SLICER")
print("##################################################")
print("TIME TO RETRIEVE")
print(time.time() - time2)

print("NUM LEAVES")
print(len(result.leaves))
result.pprint()
