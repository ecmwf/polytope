"""Per-point tags on a structured grid: the nearest search, the merged polygon rows and the bulk fold.

A resolved point carries the tags of the queries / shapes that selected it, whether the tree keeps one
leaf per point, one array leaf per row, or one bulk node per spatial sub-tree.
"""

import copy

import numpy as np
import pandas as pd
import pytest
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


def retrieve(shape, bulk=False, merge_rows=False):
    options = copy.deepcopy(HEALPIX_OPTIONS)
    options["bulk_grid_leaves"] = bulk
    api = Polytope(datacube=GribJump({}), options=options)
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


@pytest.mark.parametrize("bulk", [False, True])
def test_each_nearest_value_tags_its_own_point(bulk):
    tags = ["p0", "p1", "p2"]
    found = tags_by_point(retrieve(nearest(VALUES, tags), bulk=bulk))
    assert len(found) == len(VALUES)
    assert sorted(found.values(), key=sorted) == [{"p0"}, {"p1"}, {"p2"}]


@pytest.mark.parametrize("bulk", [False, True])
def test_two_values_nearest_to_the_same_point_share_it(bulk):
    found = tags_by_point(retrieve(nearest([VALUES[0], VALUES[0]], ["A", "B"]), bulk=bulk))
    assert list(found.values()) == [{"A", "B"}]


@pytest.mark.parametrize("bulk", [False, True])
def test_multi_value_point_matches_a_union_of_points(bulk):
    tags = ["p0", "p1", "p2"]
    multi = tags_by_point(retrieve(nearest(VALUES, tags), bulk=bulk))
    union = tags_by_point(
        retrieve(
            Union(["latitude", "longitude"], *[nearest([v], t) for v, t in zip(VALUES, tags)]),
            bulk=bulk,
        )
    )
    assert multi == union


def test_bulk_fold_and_per_row_leaves_give_the_same_point_tags():
    tags = ["p0", "p1", "p2"]
    assert tags_by_point(retrieve(nearest(VALUES, tags), bulk=True)) == tags_by_point(
        retrieve(nearest(VALUES, tags), bulk=False)
    )


def test_many_tagged_nearest_values_each_reach_exactly_one_point():
    rng = np.random.default_rng(0)
    values = rng.uniform([-5, 0], [5, 40], size=(40, 2)).tolist()
    tags = [f"r{i}" for i in range(len(values))]
    found = tags_by_point(retrieve(nearest(values, tags), bulk=True))
    counts = {}
    for point_tags in found.values():
        for tag in point_tags:
            counts[tag] = counts.get(tag, 0) + 1
    assert counts == {tag: 1 for tag in tags}


def test_nearest_search_keeps_array_leaves_as_arrays():
    tree = retrieve(nearest(VALUES, ["A", "B", "C"]))
    for leaf in tree.leaves:
        assert isinstance(leaf.values, np.ndarray) and leaf.values.dtype == np.float64


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


def test_bulk_fold_keeps_the_per_point_tags_of_merged_rows():
    rows = tags_by_point(retrieve(tagged_polygons(), merge_rows=True))
    folded = tags_by_point(retrieve(tagged_polygons(), merge_rows=True, bulk=True))
    assert folded == rows


def test_merged_rows_of_one_tag_keep_node_tags():
    shape = Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], SMALL, tag="only"))
    tree = retrieve(shape, merge_rows=True)
    for leaf in tree.leaves:
        assert leaf.tag_ids is None
        assert leaf.tags == {"only"}
