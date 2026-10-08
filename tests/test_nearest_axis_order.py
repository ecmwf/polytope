"""Nearest-point requests whose axes are given as (longitude, latitude) find the same points on every branch and on
every get/prepare: the search swaps a copy of the query points, leaving the registered points untouched."""

import copy

import numpy as np
from fake_gribjump import GribJump
from test_pruned_get import HEALPIX_OPTIONS, records

from polytope_feature.datacube.backends.fdb import FDBDatacube
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select

LAT, LON = 1.3, 12.6


def point_request(point, params=("165", "167"), realizations=("1", "2")):
    # param and realization are not compressed in HEALPIX_OPTIONS: four branches, one nearest-point search each
    return Request(
        Select("class", ["d1"]),
        Select("activity", ["ScenarioMIP"]),
        Select("dataset", ["climate-dt"]),
        Select("date", [np.datetime64("2020-01-02T01:00:00")]),
        Select("experiment", ["SSP3-7.0"]),
        Select("expver", ["0001"]),
        Select("generation", ["1"]),
        Select("levtype", ["sfc"]),
        Select("model", ["IFS-NEMO"]),
        Select("param", list(params)),
        Select("realization", list(realizations)),
        Select("resolution", ["standard"]),
        Select("stream", ["clte"]),
        Select("type", ["fc"]),
        point,
    )


def retrieve(point, **kwargs):
    api = Polytope(datacube=GribJump({}), options=copy.deepcopy(HEALPIX_OPTIONS))
    request = point_request(point, **kwargs)
    datacube = api.datacube
    assert isinstance(datacube, FDBDatacube)
    tree = api.retrieve(request)
    return api, datacube, request, tree


def test_lon_lat_point_finds_the_same_point_on_every_branch():
    _, _, _, expected = retrieve(Point(["latitude", "longitude"], [[LAT, LON]], method="nearest"))
    _, datacube, _, tree = retrieve(Point(["longitude", "latitude"], [[LON, LAT]], method="nearest"))
    want = records(expected)
    got = records(tree)
    assert len(want) == 4
    assert got == want
    assert all(len(points) == 1 for points in got.values())
    # the stored request point keeps its (longitude, latitude) order
    stored_points = datacube.nearest_search[("longitude", "latitude")][0]
    assert stored_points == [[LON, LAT]]


def test_repeated_prepare_and_get_find_the_same_point():
    # one branch: one nearest-point search per get/prepare
    point = Point(["longitude", "latitude"], [[LON, LAT]], method="nearest")
    api, datacube, request, first = retrieve(point, params=["167"], realizations=["1"])
    want = records(first)
    (want_points,) = want.values()
    for _ in range(3):
        tree = api.slice(datacube, request.polytopes())
        prepared = datacube.prepare(tree.prune())
        assert [len(leaf.values) for leaf in prepared.leaves] == [1]
        (leaf,) = prepared.leaves
        assert [(leaf.parent.values[0], leaf.values[0])] == [(lat, lon) for lat, lon, _ in want_points]
        assert records(datacube.get(tree)) == want
