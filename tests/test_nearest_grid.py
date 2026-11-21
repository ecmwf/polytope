"""The batched nearest-point search on a structured grid (``engine/nearest_grid.py``).

Every test that can be is a comparison against the search it replaces: slice the same request with the
batched resolution switched off, which leaves the per-query path (one tree descent per point, then
``FDBDatacube.nearest_lat_lon_search`` over all candidates of the request), and compare the points of the
prepared tree.  The requested points, their order and their de-duplication have to be identical, because
the coordinates and their order are the output of a point-feature request.
"""

import copy
import types

import numpy as np
import pandas as pd
import pytest
from fake_gribjump import GribJump
from test_pruned_get import HEALPIX_OPTIONS, MARS_AXES, mars_options

from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
from polytope_feature.datacube.transformations.datacube_cyclic.datacube_cyclic import (
    DatacubeAxisCyclic,
)
from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select

# ---------------------------------------------------------------------------------------------------------------------
# Requests on the two production grids, driven by the fake gribjump

HEALPIX_SELECTS = [
    Select("class", ["d1"]),
    Select("activity", ["ScenarioMIP"]),
    Select("dataset", ["climate-dt"]),
    Select("date", [pd.Timestamp("20200102T010000")]),
    Select("experiment", ["SSP3-7.0"]),
    Select("expver", ["0001"]),
    Select("generation", ["1"]),
    Select("levtype", ["sfc"]),
    Select("model", ["IFS-NEMO"]),
    Select("param", ["167"]),
    Select("realization", ["1"]),
    Select("resolution", ["standard"]),
    Select("stream", ["clte"]),
    Select("type", ["fc"]),
]

OCTAHEDRAL_SELECTS = [
    Select("step", [0]),
    Select("levtype", ["sfc"]),
    Select("date", [pd.Timestamp("20240101T000000")]),
    Select("domain", ["g"]),
    Select("expver", ["0001"]),
    Select("param", ["167"]),
    Select("class", ["od"]),
    Select("stream", ["enfo"]),
    Select("type", ["pf"]),
    Select("number", [1]),
]


def healpix(resolution=1024):
    options = copy.deepcopy(HEALPIX_OPTIONS)
    for entry in options["axis_config"]:
        if entry["axis_name"] == "values":
            entry["transformations"][0]["resolution"] = resolution
    return GribJump({}), options, HEALPIX_SELECTS


def octahedral(resolution=1280):
    mapper = {"type": "octahedral", "resolution": resolution}
    return GribJump(MARS_AXES), mars_options(mapper), OCTAHEDRAL_SELECTS


GRIDS = {"o1280": octahedral, "healpix1024": healpix}


def prepared_points(grid, shapes, batched=True, selects=None):
    """The one bulk spatial node of a prepared tree, sliced with or without the batched resolution."""
    handle, options, grid_selects = grid()
    api = Polytope(datacube=handle, options=copy.deepcopy(options))
    if not batched:
        # the per-query path: the datacube reports no axes to batch, so Points stay 1-D per axis and
        # FDBDatacube.nearest_lat_lon_search resolves them
        api.datacube._nearest_grid_axes = (None,)
    request = Request(*(grid_selects if selects is None else selects), *shapes)
    # Polytope.retrieve without the datacube.get, which is also what polytope-mars does
    api.datacube.check_branching_axes(request)
    api.switch_polytope_dim(request)
    api.datacube.nearest_search = {}
    for polytope in request.polytopes():
        if polytope.method == "nearest":
            query = polytope.values if polytope.is_flat else polytope.points
            points, _, tags = api.datacube.nearest_search.setdefault(tuple(polytope.axes()), ([], polytope.k, []))
            points.extend(list(pt) for pt in query)
            tags.extend([polytope.tag] * len(query))
    prepared = api.datacube.prepare(api.slice(api.datacube, request.polytopes()))
    nodes = prepared.leaves
    assert len(nodes) == 1, [type(node).__name__ for node in nodes]
    return nodes[0]


def nearest(points, tag=None, axes=("latitude", "longitude")):
    return Point(list(axes), [list(p) for p in points], method="nearest", tag=tag)


def assert_same_points(old, new):
    assert isinstance(new, BulkGridTensorIndexNode)
    assert new.point_count == old.point_count
    assert np.array_equal(new.coordinates, old.coordinates)
    assert np.array_equal(new.indexes, old.indexes)


# ---------------------------------------------------------------------------------------------------------------------
# The points are those of the search this replaces


@pytest.mark.parametrize("grid", sorted(GRIDS))
def test_many_scattered_points_resolve_exactly_as_the_per_query_search(grid):
    """2 000 random points, longitudes on both sides of the seam, on the production grids."""
    rng = np.random.default_rng(3)
    # outside the polar caps, where the old search's answer depends on the other points of the request
    # (see test_a_polar_cap_query_depends_on_the_rest_of_the_old_request)
    points = rng.uniform([-85.0, -180.0], [85.0, 180.0], size=(2000, 2)).tolist()
    old = prepared_points(GRIDS[grid], [nearest(points)], batched=False)
    new = prepared_points(GRIDS[grid], [nearest(points)], batched=True)
    assert_same_points(old, new)
    assert new.point_of_query.size == len(points)


@pytest.mark.parametrize("grid", sorted(GRIDS))
@pytest.mark.parametrize(
    "point",
    [
        [38.9, -9.07],  # a negative longitude: searched 360 degrees away and mapped back
        [51.5, 0.0],
        [0.0, 0.0],  # on the equator, and on a grid row of both grids
        [-0.000001, 359.9999],  # just below the seam
        # the distance is not cyclic either: a query just short of 360 degrees is resolved onto the last
        # longitude of its row, not onto the point at 0 degrees which is nearer the other way round
        # (pinned on a real datacube by tests/test_point_nearest.py)
        [0.035149384216, 359.97],
        [89.99, 180.0],
        [-89.99, -0.001],
        [90.0, 0.0],  # the pole: only one grid row brackets it
        [-90.0, 720.5],  # a longitude two turns round the axis
    ],
)
def test_single_points_resolve_exactly_as_the_per_query_search(grid, point):
    old = prepared_points(GRIDS[grid], [nearest([point])], batched=False)
    new = prepared_points(GRIDS[grid], [nearest([point])], batched=True)
    assert_same_points(old, new)


@pytest.mark.parametrize("grid", sorted(GRIDS))
def test_reversed_axes_resolve_exactly_as_the_per_query_search(grid):
    points = [[-9.07, 38.9], [12.0, 55.0]]
    shapes = [nearest(points, axes=("longitude", "latitude"))]
    assert_same_points(
        prepared_points(GRIDS[grid], shapes, batched=False),
        prepared_points(GRIDS[grid], [nearest(points, axes=("longitude", "latitude"))], batched=True),
    )


def test_a_negative_longitude_keeps_the_rounded_round_trip_value():
    """The stored longitude is the grid's, rounded to 12 decimals after being mapped round the seam.

    The search finds the grid longitude 360 degrees away and adds the offset back, which rounds the value
    twice; the result is not always the double the grid itself holds, and it is what the old path wrote
    out, so it is pinned here as well as compared against the old path.
    """
    node = prepared_points(octahedral, [nearest([[38.9, -9.07]])], batched=True)
    assert node.coordinates[0].tolist() == [38.910368186756, 350.889192886457]
    assert node.indexes.tolist() == [1070070]


# ---------------------------------------------------------------------------------------------------------------------
# Several queries on one grid point, and the mapping back to the request


@pytest.mark.parametrize("grid", sorted(GRIDS))
def test_queries_on_one_grid_point_give_one_point_as_before(grid):
    """Requested points that snap to the same grid point are still returned once, as the old search did."""
    points = [[0.01, 0.01], [0.012, 0.011], [40.0, 10.0]]
    old = prepared_points(GRIDS[grid], [nearest(points)], batched=False)
    new = prepared_points(GRIDS[grid], [nearest(points)], batched=True)
    assert_same_points(old, new)
    assert new.point_count == 2
    # the first two queries resolved to the same point, the third to its own
    first, second, third = new.point_of_query.tolist()
    assert first == second and third != first


@pytest.mark.parametrize("grid", sorted(GRIDS))
def test_point_of_query_names_the_point_each_requested_point_resolved_to(grid):
    rng = np.random.default_rng(5)
    points = rng.uniform([-80.0, 0.0], [80.0, 360.0], size=(50, 2)).tolist()
    node = prepared_points(GRIDS[grid], [nearest(points)], batched=True)
    assert node.point_of_query.shape == (50,)
    assert set(node.point_of_query.tolist()) == set(range(node.point_count))
    # the point a query is mapped to is the node's point nearest to it: the resolved points are candidates,
    # and a query is resolved to the nearest candidate of the request
    lat, lon = node.coordinates[:, 0], node.coordinates[:, 1]
    for query, point in zip(points, node.point_of_query.tolist()):
        distances = np.hypot(lat - query[0], lon - query[1] % 360)
        assert distances[point] == distances.min()


def test_tags_reach_the_points_their_queries_resolved_to():
    points = [[0.01, 0.01], [0.012, 0.011], [40.0, 10.0]]
    node = prepared_points(octahedral, [nearest(points, tag=["a", "b", "c"])], batched=True)
    tags = [set(node.tags_of_point(i)) for i in range(node.point_count)]
    assert tags == [{"a", "b"}, {"c"}] or tags == [{"c"}, {"a", "b"}]


# ---------------------------------------------------------------------------------------------------------------------
# One resolution, one node per field group


def test_every_field_group_gets_the_same_resolved_points():
    """A request with several parameters descends to one spatial node per parameter, all sharing the search."""
    selects = [s for s in OCTAHEDRAL_SELECTS if s.axis != "param"] + [Select("param", ["165", "167"])]
    handle, options, _ = octahedral()
    options = copy.deepcopy(options)
    options["compressed_axes_config"] = [a for a in options["compressed_axes_config"] if a != "param"]
    api = Polytope(datacube=handle, options=options)
    request = Request(*selects, nearest([[38.9, -9.07], [51.5, -0.12]]))
    api.datacube.check_branching_axes(request)
    api.switch_polytope_dim(request)
    api.datacube.nearest_search = {}
    prepared = api.datacube.prepare(api.slice(api.datacube, request.polytopes()))
    nodes = prepared.leaves
    assert len(nodes) == 2
    assert all(isinstance(node, BulkGridTensorIndexNode) for node in nodes)
    assert np.array_equal(nodes[0].coordinates, nodes[1].coordinates)
    # the same arrays, not two copies of them: the search ran once
    assert nodes[0].indexes is nodes[1].indexes


def test_healpix_rows_by_index_are_the_rows_by_latitude():
    """The search takes a row's longitudes by row index, which must be the row ``second_axis_vals`` finds.

    ``NestedHealpixGridMapper.second_axis_vals`` looks the row index up by scanning every row latitude,
    which costs more than building the row; ``second_axis_vals_from_idx`` skips the scan.
    """
    from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix_nested import (
        NestedHealpixGridMapper,
    )

    mapper = NestedHealpixGridMapper("values", ["latitude", "longitude"], 128)
    rows = mapper.first_axis_vals()
    for index in range(0, len(rows), 7):
        by_index = np.asarray(mapper.second_axis_vals_from_idx(index), dtype=np.float64)
        by_value = np.asarray(mapper.second_axis_vals((rows[index],)), dtype=np.float64)
        assert np.array_equal(by_index, by_value)


# ---------------------------------------------------------------------------------------------------------------------
# What the batched search reproduces rather than fixes


def test_a_query_is_resolved_against_the_candidates_of_the_whole_request():
    """A point's result depends on the other points of the request, and still does.

    The old search matched every query against the candidate tree of the whole request, so a query can be
    resolved onto a grid point outside its own four candidates: here one point on its own lands on the grid
    row below it, and with a second point 0.3 degrees away in the request both land on the row above, which
    the second point brought in.  It is preserved, because the coordinates of a request's result are its
    output.  Where it bites is wherever a grid row's longitude spacing is wider than the latitude spacing
    of its neighbours, which on a reduced grid is everywhere but the equator.
    """
    cap = [-83.12174141, 1.20112128]
    neighbour = [-82.8, 2.3]

    def grid():
        return healpix(128)  # coarse enough that the rings near the pole hold few points

    for batched in (False, True):
        alone = prepared_points(grid, [nearest([cap])], batched=batched).coordinates.tolist()
        together = prepared_points(grid, [nearest([cap, neighbour])], batched=batched).coordinates.tolist()
        assert alone == [[-83.051568163977, 2.368421052632]]
        # both requested points collapse onto one grid point of the row above
        assert together == [[-82.685376210764, 2.25]]


# ---------------------------------------------------------------------------------------------------------------------
# The quadtree slicer maps a nearest query into the cyclic longitude range too


def cyclic_longitude_axis(axis, axis_range=(0, 360)):
    axis = copy.deepcopy(axis)
    axis.transformations = [DatacubeAxisCyclic("longitude", types.SimpleNamespace(range=list(axis_range)))]
    axis.is_cyclic = True
    return axis


def test_a_quadtree_nearest_query_is_mapped_into_the_cyclic_longitude_range():
    """A negative longitude against a [0, 360] point cloud used to snap to the cloud's smallest longitude."""
    from polytope_feature.datacube.datacube_axis import FloatDatacubeAxis
    from polytope_feature.shapes import ConvexPolytope

    lat_ax, lon_ax = FloatDatacubeAxis(), FloatDatacubeAxis()
    lat_ax.name, lon_ax.name = "latitude", "longitude"
    cloud = [(lat, lon) for lat in (0.0, 1.0) for lon in (0.0, 10.0, 350.0, 355.0)]
    slicer = QuadTreeSlicer(cloud)
    datacube = types.SimpleNamespace(
        _axes={"latitude": lat_ax, "longitude": cyclic_longitude_axis(lon_ax)},
        nearest_search={},
    )
    query = ConvexPolytope(["latitude", "longitude"], [[0.1, -9.0]], method="nearest", k=1)
    (index,) = slicer.extract_single(datacube, query)
    assert list(cloud[index]) == [0.0, 350.0]

    # without a cyclic axis the query keeps its own value, and the nearest point is the smallest longitude
    plain = types.SimpleNamespace(_axes={"latitude": lat_ax, "longitude": lon_ax})
    (index,) = slicer.extract_single(plain, query)
    assert list(cloud[index]) == [0.0, 0.0]
