"""Per-point tags on a structured grid: the nearest search, the merged polygon rows and the bulk fold.

A resolved point carries the tags of the queries / shapes that selected it, whether the sliced tree keeps
one leaf per point or one array leaf per row, and whatever the fold does with those rows.
"""

import copy

import numpy as np
import pandas as pd
from fake_gribjump import GribJump
from test_pruned_get import HEALPIX_OPTIONS

from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Polygon, Select, Union

SELECTS = [
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


def retrieve(shape, merge_rows=False):
    api = Polytope(datacube=GribJump({}), options=copy.deepcopy(HEALPIX_OPTIONS))
    api._merge_union_rows = merge_rows
    return api.retrieve(Request(*SELECTS, shape))


def tags_by_point(tree):
    """``{(lat, lon): tags}`` over every point of a filled tree, whatever leaf kind it holds."""
    out = {}
    for leaf in tree.leaves:
        if isinstance(leaf, BulkGridTensorIndexNode):
            for i, (lat, lon) in enumerate(leaf.coordinates.tolist()):
                out.setdefault((lat, lon), set()).update(leaf.tags_of_point(i))
            continue
        lat = leaf.parent.values[0]
        for i, lon in enumerate(np.asarray(leaf.values).tolist()):
            out.setdefault((lat, lon), set()).update(leaf.tags_of_point(i))
    return out


def nearest(values, tags):
    return Point(["latitude", "longitude"], values, method="nearest", tag=tags)


VALUES = [[0.0, 0.0], [1.3, 12.6], [-2.5, 30.0]]


# ---------------------------------------------------------------------------------------------------------------------
# nearest search


def test_each_nearest_value_tags_its_own_point():
    tags = ["p0", "p1", "p2"]
    found = tags_by_point(retrieve(nearest(VALUES, tags)))
    assert len(found) == len(VALUES)
    assert sorted(found.values(), key=sorted) == [{"p0"}, {"p1"}, {"p2"}]


def test_two_values_nearest_to_the_same_point_share_it():
    found = tags_by_point(retrieve(nearest([VALUES[0], VALUES[0]], ["A", "B"])))
    assert list(found.values()) == [{"A", "B"}]


def test_multi_value_point_matches_a_union_of_points():
    tags = ["p0", "p1", "p2"]
    multi = tags_by_point(retrieve(nearest(VALUES, tags)))
    union = tags_by_point(retrieve(Union(["latitude", "longitude"], *[nearest([v], t) for v, t in zip(VALUES, tags)])))
    assert multi == union


def test_many_tagged_nearest_values_each_reach_exactly_one_point():
    rng = np.random.default_rng(0)
    values = rng.uniform([-5, 0], [5, 40], size=(40, 2)).tolist()
    tags = [f"r{i}" for i in range(len(values))]
    found = tags_by_point(retrieve(nearest(values, tags)))
    counts = {}
    for point_tags in found.values():
        for tag in point_tags:
            counts[tag] = counts.get(tag, 0) + 1
    assert counts == {tag: 1 for tag in tags}


def test_nearest_search_keeps_the_points_in_arrays():
    """The resolved points live in the bulk node's arrays: no Python object per point."""
    tree = retrieve(nearest(VALUES, ["A", "B", "C"]))
    for leaf in tree.leaves:
        assert leaf.coordinates.dtype == np.float64 and leaf.indexes.dtype == np.int64
        assert leaf.point_count == len(VALUES)


# ---------------------------------------------------------------------------------------------------------------------
# merged polygon rows


SMALL = [[0, 0], [0, 6], [4, 6], [2, 3], [4, 0]]
SHIFTED = [[p[0], p[1] + 10] for p in SMALL]


def tagged_polygons():
    return Union(
        ["latitude", "longitude"],
        Polygon(["latitude", "longitude"], SMALL, tag="a"),
        Polygon(["latitude", "longitude"], SHIFTED, tag="b"),
    )


def test_merged_rows_carry_the_tag_of_each_piece():
    per_point = tags_by_point(retrieve(tagged_polygons()))
    rows = tags_by_point(retrieve(tagged_polygons(), merge_rows=True))
    assert rows == per_point
    assert {"a"} in rows.values() and {"b"} in rows.values()


def test_merged_rows_of_one_tag_keep_node_tags():
    shape = Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], SMALL, tag="only"))
    tree = retrieve(shape, merge_rows=True)
    for leaf in tree.leaves:
        assert leaf.tag_ids is None
        assert leaf.tags == {"only"}
