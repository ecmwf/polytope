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

from ..tests.helper_functions import download_test_data
# os.environ["FDB_HOME"] = "/Users/male/git/fdb-new-home"

# slicer_type = "quadtree"
# file_name = "../../Downloads/icon_grid_0026_R03B07_G.nc"

nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
download_test_data(nexus_url, "foo.grib")

file_name = "../tests/data/foo.grib"

ds = data.from_source("file", "./tests/data/foo.grib")


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
    # grid = xr.open_dataset(file_name, engine="netcdf4")
    grid = data.from_source("file", file_name)

    longitudes = grid.longitude.values * 180/math.pi
    latitudes = grid.latitude.values * 180/math.pi

    points = list(zip(latitudes, longitudes))
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
                        "latitude", "longitude"], "md5_hash": "f68071a8ac9bae4e965822afb963c04f"}
                ],
            },
        ],
        "pre_path": {"date": "20250110"},
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
        "axis_config": [
            {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
            {
                "axis_name": "date",
                "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
            },
            {
                "axis_name": "values",
                "transformations": [
                    {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": [
                        "latitude", "longitude"]}
                ],
            },
        ],
        "pre_path": {"date": "20250110"},
    }

    fdbdatacube = gj.GribJump()

    engine_options = get_engine_options("hullslicer")

    API = Polytope(
        datacube=fdbdatacube,
        options=options,
        engine_options=engine_options,
    )

    return API


# Compare boxes of different sizes


# Compare polygons with n vertices
