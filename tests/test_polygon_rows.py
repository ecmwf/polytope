"""Polygons sliced into one longitude leaf per latitude node give the same points, in the same order, as one leaf
per point, and ``prepare``/``get``/``prune`` behave identically on both trees (fake gribjump)."""

import itertools

import numpy as np
import pandas as pd
import pytest
from fake_gribjump import GribJump, index_of
from test_pruned_get import (
    HEALPIX_OPTIONS,
    MARS_AXES,
    assert_same_records,
    full_records,
    iter_nodes,
    mars_options,
    selected_records,
    snapshot,
)

from polytope_feature.datacube.backends.fdb import FDBDatacube
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Polygon, Select, Union

# (lat, lon) vertices.  Every polygon is non-convex, so it is cut into several triangles.
# A notched polygon whose concavity leaves a gap in the middle of some rows.
NOTCHED = [[0, 0], [0, 30], [20, 30], [10, 20], [20, 15], [10, 10], [20, 0]]
# Crosses the longitude seam (0/360) with a notch on the seam.
SEAM = [[-10, -20], [-10, 20], [10, 25], [4, 0], [10, -25]]
# The same two shapes, scaled for the finer grids.
HEALPIX_NOTCHED = [[p[0] / 4, 10 + p[1] / 4] for p in NOTCHED]
HEALPIX_SEAM = [[p[0] / 4, p[1] / 4] for p in SEAM]
O1280_NOTCHED = [[p[0] / 40, 10 + p[1] / 40] for p in NOTCHED]
O1280_SEAM = [[p[0] / 40, p[1] / 40] for p in SEAM]


def polygon(points, tag=None):
    return Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], points, tag=tag))


def mars_polygon_request(*shapes):
    return Request(
        Select("step", [0, 6]),
        Select("levtype", ["sfc"]),
        Select("date", [pd.Timestamp("20240101T000000")]),
        Select("domain", ["g"]),
        Select("expver", ["0001"]),
        Select("param", ["165", "167"]),
        Select("class", ["od"]),
        Select("stream", ["enfo"]),
        Select("type", ["pf"]),
        Select("number", [1, 2]),
        *shapes,
    )


def healpix_polygon_request(*shapes):
    return Request(
        Select("class", ["d1"]),
        Select("activity", ["ScenarioMIP"]),
        Select("dataset", ["climate-dt"]),
        Select("date", [pd.Timestamp("20200102T010000")]),
        Select("experiment", ["SSP3-7.0"]),
        Select("expver", ["0001"]),
        Select("generation", ["1"]),
        Select("levtype", ["sfc"]),
        Select("model", ["IFS-NEMO"]),
        Select("param", ["165", "167"]),
        Select("realization", ["1", "2"]),
        Select("resolution", ["standard"]),
        Select("stream", ["clte"]),
        Select("type", ["fc"]),
        *shapes,
    )


REGULAR = mars_options({"type": "regular", "resolution": 30})
O1280 = mars_options({"type": "octahedral", "resolution": 1280})
MARS_SELECT = ["param", "step", "number"]
HEALPIX_SELECT = ["param", "realization"]

# id -> (options, gribjump axes, request factory, polygon vertices, axes to select on)
CASES = {
    "regular_notched": (REGULAR, MARS_AXES, mars_polygon_request, NOTCHED, MARS_SELECT),
    "regular_seam": (REGULAR, MARS_AXES, mars_polygon_request, SEAM, MARS_SELECT),
    "healpix_nested_notched": (HEALPIX_OPTIONS, None, healpix_polygon_request, HEALPIX_NOTCHED, HEALPIX_SELECT),
    "healpix_nested_seam": (HEALPIX_OPTIONS, None, healpix_polygon_request, HEALPIX_SEAM, HEALPIX_SELECT),
    "o1280_notched": (O1280, MARS_AXES, mars_polygon_request, O1280_NOTCHED, MARS_SELECT),
    "o1280_seam": (O1280, MARS_AXES, mars_polygon_request, O1280_SEAM, MARS_SELECT),
}


def slice_polygon(case, merge_rows, missing=None, shapes=None):
    options, axes, make_request, points, select_axes = CASES[case]
    gj = GribJump(axes or {}, missing=missing)
    api = Polytope(datacube=gj, options=options)
    api._merge_union_rows = merge_rows
    datacube = api.datacube
    assert isinstance(datacube, FDBDatacube)
    request = make_request(*(shapes or [polygon(points)]))
    datacube.check_branching_axes(request)
    tree = api.slice(datacube, request.polytopes())
    return datacube, tree, select_axes


def both_trees(case, **kwargs):
    old = slice_polygon(case, merge_rows=False, **kwargs)
    new = slice_polygon(case, merge_rows=True, **kwargs)
    return old, new


def latitude_nodes(tree):
    return [node for node, _ in iter_nodes(tree) if node is not tree and node.axis.name == "latitude"]


def point_sequence(tree):
    """[(non-spatial path, lat, lon), ...] for every point of the tree, in traversal order."""
    out = []
    for node, ancestors in iter_nodes(tree):
        if len(node.children) != 0 or node is tree:
            continue
        if hasattr(node, "coordinates"):
            # a prepared or filled tree: one bulk node per spatial sub-tree
            path = tuple((n.axis.name, tuple(n.values)) for n in ancestors[:-1])
            out.extend((path, lat, lon) for lat, lon in node.coordinates.tolist())
            continue
        field_nodes, lat_node = ancestors[:-2], ancestors[-2]
        path = tuple((n.axis.name, tuple(n.values)) for n in field_nodes)
        out.extend((path, lat_node.values[0], lon) for lon in node.values.tolist())
    return out


def prepared(datacube, tree):
    copy = tree.prune()
    assert datacube.prepare(copy) is copy
    return copy


@pytest.mark.parametrize("case", list(CASES))
def test_polygon_is_cut_into_several_pieces(case):
    points = CASES[case][3]
    assert len(Polygon(["latitude", "longitude"], points).polytope()) > 2


@pytest.mark.parametrize("case", list(CASES))
def test_polygon_rows_hold_the_per_point_leaves_in_order(case):
    (_, old, _), (_, new, _) = both_trees(case)
    # old: one leaf per point; new: one array leaf per latitude node
    assert all(len(leaf.values) == 1 for leaf in old.leaves)
    new_lats = latitude_nodes(new)
    assert all(len(lat.children) == 1 for lat in new_lats)
    assert any(len(lat.children[0].values) > 1 for lat in new_lats)
    for leaf in new.leaves:
        assert isinstance(leaf.values, np.ndarray) and leaf.values.dtype == np.float64
        assert np.all(np.diff(leaf.values) > 0)
    assert [lat.values for lat in new_lats] == [lat.values for lat in latitude_nodes(old)]
    assert point_sequence(new) == point_sequence(old)
    assert [len(leaf.values) for leaf in new.leaves] == [len(lat.children) for lat in latitude_nodes(old)]
    assert len(new.leaves) < len(old.leaves)


@pytest.mark.parametrize("case", list(CASES))
def test_polygon_get_matches_per_point_tree(case):
    (old_cube, old, _), (new_cube, new, _) = both_trees(case)
    old_filled, old_records = full_records(old_cube, old)
    new_filled, new_records = full_records(new_cube, new)
    assert_same_records(old_records, new_records)
    assert point_sequence(new_filled) == point_sequence(old_filled)
    mapper = new_cube.grid_transformation
    for points in new_records.values():
        for lat, lon, value in points:
            grid_index = mapper.unmap([lat], [lon])[0]
            assert index_of(value) == grid_index
    if case.startswith("healpix"):
        # nested grid indices are not ascending along a row, so the results of a merged row really were
        # put back into the row's value order after being fetched in grid-index order
        assert any(bool(np.any(np.diff(leaf.indexes) < 0)) for leaf in new_filled.leaves)


@pytest.mark.parametrize("case", list(CASES))
def test_prepare_on_polygon_rows_matches_per_point_tree(case):
    (old_cube, old, _), (new_cube, new, _) = both_trees(case)
    old_prepared = prepared(old_cube, old)
    new_prepared = prepared(new_cube, new)
    assert point_sequence(new_prepared) == point_sequence(old_prepared)
    # prepare leaves the merged rows in ascending order and is idempotent
    assert point_sequence(new_prepared) == point_sequence(new)
    again = prepared(new_cube, new_prepared)
    assert snapshot(again) == snapshot(new_prepared)
    _, full = full_records(new_cube, new)
    _, from_prepared = full_records(new_cube, new_prepared)
    assert_same_records(full, from_prepared)


@pytest.mark.parametrize("case", list(CASES))
def test_pruned_gets_of_polygon_rows_reproduce_per_point_get(case):
    (old_cube, old, select_axes), (new_cube, new, _) = both_trees(case)
    _, old_full = full_records(old_cube, old)
    before = snapshot(new)
    pruned = selected_records(new_cube, new, select_axes)
    assert_same_records(old_full, pruned)
    assert snapshot(new) == before
    # sub-trees of the prepared tree too
    new_prepared = prepared(new_cube, new)
    pruned = selected_records(new_cube, new_prepared, select_axes)
    assert_same_records(old_full, pruned)


@pytest.mark.parametrize("case", ["regular_seam", "healpix_nested_notched"])
def test_polygon_rows_with_missing_field(case):
    field = {"param": "165"}
    (old_cube, old, select_axes), (new_cube, new, _) = both_trees(case, missing=[field])
    _, old_full = full_records(old_cube, old)
    _, new_full = full_records(new_cube, new)
    assert_same_records(old_full, new_full)
    assert any(v is None for points in new_full.values() for _, _, v in points)
    pruned = selected_records(new_cube, new, select_axes)
    assert_same_records(old_full, pruned)


def test_polygon_rows_keep_the_polygon_tag():
    shapes = [polygon(NOTCHED, tag="area")]
    (_, old, _), (_, new, _) = both_trees("regular_notched", shapes=shapes)
    assert {frozenset(leaf.tags) for leaf in old.leaves} == {frozenset({"area"})}
    assert {frozenset(leaf.tags) for leaf in new.leaves} == {frozenset({"area"})}
    assert point_sequence(new) == point_sequence(old)


def test_polygons_with_different_tags_compress_with_per_point_tags():
    """Two tagged polygons sharing rows merge into one leaf per row, each point keeping its own tag."""
    second = [[p[0], p[1] + 25] for p in NOTCHED]
    shapes = [
        Union(
            ["latitude", "longitude"],
            Polygon(["latitude", "longitude"], NOTCHED, tag="a"),
            Polygon(["latitude", "longitude"], second, tag="b"),
        )
    ]
    (_, old, _), (_, new, _) = both_trees("regular_notched", shapes=shapes)
    assert point_sequence(new) == point_sequence(old)
    assert any(len(leaf.values) > 1 for leaf in new.leaves)
    # every point carries the tag of the polygon it came from, as it did on its own leaf
    old_tags = {(lat, lon): leaf.tags for leaf in old.leaves for lat, lon in [(leaf.parent.values[0], leaf.values[0])]}
    new_tags = {}
    for leaf in new.leaves:
        for i, lon in enumerate(leaf.values.tolist()):
            new_tags[(leaf.parent.values[0], lon)] = set(leaf.tags_of_point(i))
    assert new_tags == old_tags
    assert {frozenset({"a"}), frozenset({"b"})} <= {frozenset(t) for t in new_tags.values()}


def test_overlapping_polygons_give_each_point_once():
    shifted = [[p[0] + 5, p[1] + 6] for p in NOTCHED]
    shapes = [
        Union(
            ["latitude", "longitude"],
            Polygon(["latitude", "longitude"], NOTCHED),
            Polygon(["latitude", "longitude"], shifted),
        )
    ]
    (old_cube, old, _), (new_cube, new, _) = both_trees("regular_notched", shapes=shapes)
    assert point_sequence(new) == point_sequence(old)
    for leaf in new.leaves:
        assert len(np.unique(leaf.values)) == len(leaf.values)
    _, old_full = full_records(old_cube, old)
    _, new_full = full_records(new_cube, new)
    assert_same_records(old_full, new_full)


def test_merged_rows_flag_survives_pruning():
    _, (new_cube, new, _) = both_trees("healpix_nested_seam")
    leaves = new.prune(select={"param": "167"}).leaves
    assert len(leaves) > 0 and all(leaf._keep_value_order for leaf in leaves)
    _, fields = full_records(new_cube, new)
    assert len(fields) == len(list(itertools.product(["165", "167"], ["1", "2"])))
