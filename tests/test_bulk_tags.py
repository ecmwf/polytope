"""Unit tests (no FDB needed) for per-point tags on bulk leaves, the nearest-search tag
re-attachment, the quadtree engine's per-polytope tagging and the engine batching used by
Polytope.slice()."""

import numpy as np
import pytest
import xarray as xr
from bulk_helpers import point_leaves

from polytope_feature.datacube.backends.fdb import FDBDatacube
from polytope_feature.datacube.datacube_axis import FloatDatacubeAxis
from polytope_feature.datacube.tensor_index_tree import (
    BulkGridTensorIndexNode,
    BulkMergedTensorIndexNode,
    TensorIndexTree,
)
from polytope_feature.engine.engine import Engine
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import ConvexPolytope, Point, Product, Union


def float_axis(name):
    ax = FloatDatacubeAxis()
    ax.name = name
    return ax


LAT, LON = float_axis("latitude"), float_axis("longitude")


def point_tags(node):
    """Per-point tags of a bulk node, as one set per point."""
    return [set(node.tags_of_point(i)) for i in range(node.point_count)]


# ---------------------------------------------------------------------------
# Bulk leaves carry one set of tags per point
# ---------------------------------------------------------------------------


class TestBulkMergedNodeTags:
    def test_default_point_tags_are_empty(self):
        node = BulkMergedTensorIndexNode([LAT, LON], [[0, 0], [1, 1]], [3, 4])
        assert point_tags(node) == [set(), set()]
        assert node.tags == set()

    def test_point_tags_are_aligned_and_unioned_on_node(self):
        node = BulkMergedTensorIndexNode([LAT, LON], [[0, 0], [1, 1]], [3, 4], [{"a"}, {"b", "c"}])
        assert point_tags(node) == [{"a"}, {"b", "c"}]
        assert node.tags == {"a", "b", "c"}

    def test_point_tags_must_match_point_count(self):
        with pytest.raises(AssertionError):
            BulkMergedTensorIndexNode([LAT, LON], [[0, 0], [1, 1]], [3, 4], [{"a"}])

    def test_point_tags_are_copied(self):
        tags = [{"a"}]
        node = BulkMergedTensorIndexNode([LAT, LON], [[0, 0]], [3], tags)
        tags[0].add("x")
        assert point_tags(node) == [{"a"}]

    def test_merge_unions_tags_of_shared_points_and_keeps_alignment(self):
        first = BulkMergedTensorIndexNode([LAT, LON], [[2, 0], [0, 0]], [20, 0], [{"a"}, {"b"}])
        second = BulkMergedTensorIndexNode([LAT, LON], [[0, 0], [1, 0]], [0, 10], [{"c"}, set()])
        first.merge(second)
        # sorted by (lat, lon), duplicates of index 0 merged with the union of their tags
        assert first.indexes.tolist() == [0, 10, 20]
        assert first.coordinates[:, 0].tolist() == [0, 1, 2]
        assert point_tags(first) == [{"b", "c"}, set(), {"a"}]
        assert first.tags == {"a", "b", "c"}

    def test_create_bulk_merged_child_merges_point_tags(self):
        parent = TensorIndexTree()
        parent.create_bulk_merged_child([LAT, LON], [[0, 0]], [0], [], point_tags=[{"a"}])
        node, _ = parent.create_bulk_merged_child([LAT, LON], [[0, 0], [1, 1]], [0, 1], [], point_tags=[{"b"}, {"c"}])
        assert len(parent.children) == 1
        assert point_tags(node) == [{"a", "b"}, {"c"}]


class TestBulkGridNodeTags:
    def test_default_point_tags_are_empty(self):
        node = BulkGridTensorIndexNode([LAT, LON], [0, 1], [[0, 1], [5]], [0, 1, 2])
        assert point_tags(node) == [set(), set(), set()]

    def test_point_tags_follow_latitude_major_order(self):
        node = BulkGridTensorIndexNode([LAT, LON], [0, 1], [[0, 1], [5]], [0, 1, 2], [{"a"}, {"b"}, {"c"}])
        assert node.coordinates.tolist() == [[0, 0], [0, 1], [1, 5]]
        assert point_tags(node)[node.row_slice(0)] == [{"a"}, {"b"}]
        assert point_tags(node)[node.row_slice(1)] == [{"c"}]
        assert node.tags == {"a", "b", "c"}

    def test_point_leaf_exposes_point_tags(self):
        root = TensorIndexTree()
        root.add_child(BulkGridTensorIndexNode([LAT, LON], [0], [[0, 1]], [0, 1], [{"a"}, {"b"}]))
        assert [leaf.tags for leaf in point_leaves(root)] == [{"a"}, {"b"}]


# ---------------------------------------------------------------------------
# Nearest search: tags re-attached to the point each query is nearest to
# ---------------------------------------------------------------------------


def lat_lon_tree(lon_nodes, lat_tags=()):
    """A latitude node at 0 with one longitude child per (values, tags) in lon_nodes."""
    lat = TensorIndexTree(LAT, (0.0,))
    lat.tags = set(lat_tags)
    for values, tags in lon_nodes:
        lon = TensorIndexTree(LON, tuple(values))
        lon.tags = set(tags)
        lat.add_child(lon)
    root = TensorIndexTree()
    root.add_child(lat)
    return lat


def lon_tags(lat):
    return {value: lon.tags for lon in lat.children for value in lon.values}


class TestRetagNearestLons:
    def test_splits_compressed_node_with_points_nearest_to_different_queries(self):
        lat = lat_lon_tree([((0.0, 0.5), {"A", "B"})], lat_tags={"A", "B"})
        FDBDatacube._retag_nearest_lons(lat, {(0.0, 0.0): {"A"}, (0.0, 0.5): {"B"}}, {"A", "B"})
        assert lon_tags(lat) == {0.0: {"A"}, 0.5: {"B"}}
        assert len(lat.children) == 2
        assert lat.tags == set()

    def test_point_nearest_to_several_queries_gets_all_their_tags(self):
        lat = lat_lon_tree([((0.0,), {"A", "B"})])
        FDBDatacube._retag_nearest_lons(lat, {(0.0, 0.0): {"A", "B"}}, {"A", "B"})
        assert lon_tags(lat) == {0.0: {"A", "B"}}

    def test_merges_overlapping_siblings(self):
        lat = lat_lon_tree([((0.0, 0.5), {"A"}), ((0.5, 1.0), {"B"})])
        FDBDatacube._retag_nearest_lons(lat, {(0.0, 0.0): {"A"}, (0.0, 0.5): {"B"}}, {"A", "B"})
        assert sorted(v for lon in lat.children for v in lon.values) == [0.0, 0.5, 1.0]
        assert lon_tags(lat) == {0.0: {"A"}, 0.5: {"B"}, 1.0: set()}

    def test_keeps_tags_not_coming_from_the_nearest_search(self):
        lat = lat_lon_tree([((0.0, 0.5), {"A", "other"})], lat_tags={"lat_tag", "A"})
        FDBDatacube._retag_nearest_lons(lat, {(0.0, 0.0): {"A"}}, {"A"})
        assert lat.tags == {"lat_tag"}
        assert lon_tags(lat) == {0.0: {"A", "other"}, 0.5: {"other"}}

    def test_single_group_keeps_existing_node(self):
        lat = lat_lon_tree([((0.0, 0.5), {"A"})])
        node = next(iter(lat.children))
        FDBDatacube._retag_nearest_lons(lat, {(0.0, 0.0): {"A"}, (0.0, 0.5): {"A"}}, {"A"})
        assert next(iter(lat.children)) is node
        assert node.tags == {"A"}


# ---------------------------------------------------------------------------
# Quadtree engine: every polytope resolved, and tagged, on its own
# ---------------------------------------------------------------------------


class _Cube:
    # bulk leaves are opt-in on the datacube (the ``bulk_grid_leaves`` option)
    bulk_grid_leaves = True

    def __init__(self):
        self._axes = {"latitude": LAT, "longitude": LON}


GRID = [(lat, lon) for lat in np.arange(0.0, 5.0) for lon in np.arange(0.0, 5.0)]


def quadtree_leaf(*polytopes):
    slicer = QuadTreeSlicer(GRID)
    root = TensorIndexTree()
    node = TensorIndexTree(float_axis("step"), (0,))
    root.add_child(node)
    node["unsliced_polytopes"] = set(polytopes)
    slicer._build_branch(LAT, node, _Cube(), [], None)
    assert len(node.children) <= 1
    if len(node.children) == 0:
        return {}
    bulk = next(iter(node.children))
    return {tuple(c): set(bulk.tags_of_point(i)) for i, c in enumerate(bulk.coordinates.tolist())}


def nearest(point, tag, k=1):
    return ConvexPolytope(["latitude", "longitude"], [point], method="nearest", k=k, tag=tag)


class TestQuadTreeTags:
    def test_each_nearest_query_tags_its_own_point(self):
        tags = quadtree_leaf(nearest([1.1, 1.2], "A"), nearest([3.2, 2.9], "B"))
        assert tags == {(1.0, 1.0): {"A"}, (3.0, 3.0): {"B"}}

    def test_queries_with_same_nearest_point_accumulate_tags(self):
        tags = quadtree_leaf(nearest([1.1, 1.2], "A"), nearest([0.9, 0.8], "B"))
        assert tags == {(1.0, 1.0): {"A", "B"}}

    def test_k_nearest_points_all_carry_the_query_tag(self):
        tags = quadtree_leaf(nearest([1.0, 1.4], "A", k=2))
        assert tags == {(1.0, 1.0): {"A"}, (1.0, 2.0): {"A"}}

    def test_reversed_axes(self):
        poly = ConvexPolytope(["longitude", "latitude"], [[3.1, 1.2]], method="nearest", k=1, tag="A")
        assert quadtree_leaf(poly) == {(1.0, 3.0): {"A"}}

    def test_polygon_and_untagged_polytopes(self):
        box = ConvexPolytope(["latitude", "longitude"], [[0, 0], [0, 1], [1, 0], [1, 1]], tag="box")
        tags = quadtree_leaf(box, nearest([4.1, 4.1], None))
        assert tags == {
            (0.0, 0.0): {"box"},
            (0.0, 1.0): {"box"},
            (1.0, 0.0): {"box"},
            (1.0, 1.0): {"box"},
            (4.0, 4.0): set(),
        }

    def test_python_knn_fallback_matches(self):
        slicer = QuadTreeSlicer(GRID)
        assert [GRID[i] for i in slicer._python_knn((1.0, 1.4), 2)] == [(1.0, 1.0), (1.0, 2.0)]


# ---------------------------------------------------------------------------
# Engines declare whether they batch polytopes; slice() groups combinations
# ---------------------------------------------------------------------------


class TestEngineBatching:
    def test_engine_flags(self):
        assert Engine.batches_polytopes is False
        assert HullSlicer.batches_polytopes is False
        assert QuadTreeSlicer.batches_polytopes is True

    def test_group_combinations_shares_prefix(self):
        step = ConvexPolytope(["step"], [[0]], is_orthogonal=True)
        points = [nearest([i, i], f"t{i}") for i in range(3)]
        combinations = [([step], p) for p in points]
        spatial = {"latitude", "longitude"}
        groups = list(Polytope._group_combinations(combinations, lambda p: spatial.intersection(p.axes())))
        assert len(groups) == 1
        shared, batched = groups[0]
        assert shared == [step]
        # the batched polytopes keep the order of the request
        assert batched == points

    def test_group_combinations_without_batching_engine_keeps_every_combination(self):
        step = ConvexPolytope(["step"], [[0]], is_orthogonal=True)
        combinations = [([step], p) for p in (nearest([0, 0], None), nearest([1, 1], None))]
        assert len(list(Polytope._group_combinations(combinations, lambda p: False))) == 2


# ---------------------------------------------------------------------------
# Point values and the nearest-search registry
# ---------------------------------------------------------------------------


def xarray_api():
    array = xr.DataArray(
        np.arange(50, dtype=float).reshape(5, 10), dims=("step", "level"), coords={"step": range(5), "level": range(10)}
    )
    return Polytope(datacube=array, options={})


class TestPointValues:
    def test_value_tag(self):
        assert Point(["a", "b"], [[0, 0], [1, 1]], tag=["x", "y"]).value_tag(1) == "y"
        assert Point(["a", "b"], [[0, 0], [1, 1]], tag="x").value_tag(1) == "x"
        # a list which does not match the values is a single tag
        assert Point(["a", "b"], [[0, 0], [1, 1]], tag=["x"]).value_tag(1) == ["x"]

    def test_several_values_behave_as_a_union(self):
        polys = Point(["a", "b"], [[0, 0], [1, 1]], tag=["x", "y"]).polytope()
        assert all(isinstance(p, Product) and p.is_in_union for p in polys)
        assert [p.tag for p in polys] == ["x", "y"]

    def test_single_value_is_not_a_union(self):
        (poly,) = Point(["a", "b"], [[0, 0]]).polytope()
        assert not poly.is_in_union

    def test_nearest_registry_holds_tags_and_is_reset_per_request(self):
        api = xarray_api()
        api.retrieve(Request(Point(["step", "level"], [[1, 2], [3, 4]], method="nearest", tag=["x", "y"])))
        points, k, tags = api.datacube.nearest_search[("step", "level")]
        assert points == [[1, 2], [3, 4]] and k == 1 and tags == ["x", "y"]
        api.retrieve(Request(Point(["step", "level"], [[0, 0]], method="nearest", tag="z")))
        assert api.datacube.nearest_search[("step", "level")] == ([[0, 0]], 1, ["z"])

    def test_registry_does_not_alias_point_values(self):
        values = [[1, 2]]
        api = xarray_api()
        api.retrieve(Request(Union(["step", "level"], Point(["step", "level"], values, method="nearest"))))
        api.datacube.nearest_search[("step", "level")][0].append([0, 0])
        assert values == [[1, 2]]
