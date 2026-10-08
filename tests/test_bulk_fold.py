"""The ``bulk_grid_leaves`` fold of a structured tree: same points, same order, same values.

Drives the real ``FDBDatacube`` against the in-memory fake gribjump (``tests/fake_gribjump.py``) with
the fold off and on and compares the ordered ``(latitude, longitude)`` list and the per-field values,
which is what makes the CovJSON bytes of the two paths identical.
"""

import itertools

import numpy as np
import pytest
from fake_gribjump import GribJump, index_of
from test_pruned_get import (
    CASES,
    HEALPIX_OPTIONS,
    MARS_AXES,
    healpix_request,
    iter_nodes,
    mars_options,
    mars_request,
    records,
    same_value,
)

from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Polygon, Select, Union

# ---------------------------------------------------------------------------------------------------------------------
# Helpers

EUROPE_POLYGON = [[35, -10], [35, 30], [45, 40], [60, 40], [71, 30], [71, -10], [60, -15], [35, -10]]


def bulk_options(options):
    return dict(options, bulk_grid_leaves=True)


def slice_tree(options, axes, request, bulk, merge_rows=False, missing=None, nan_indices=None):
    gj = GribJump(axes or {}, missing=missing, nan_indices=nan_indices)
    api = Polytope(datacube=gj, options=bulk_options(options) if bulk else options)
    api._merge_union_rows = merge_rows
    api.datacube.check_branching_axes(request)
    api.switch_polytope_dim(request)
    api.datacube.nearest_search = {}
    tree = api.slice(api.datacube, request.polytopes())
    return api.datacube, tree


def bulk_records(tree):
    """``{field: [(lat, lon, value), ...]}`` of a filled tree holding bulk grid nodes."""
    out = {}
    for node, ancestors in iter_nodes(tree):
        if not isinstance(node, BulkGridTensorIndexNode):
            continue
        field_nodes = ancestors[:-1]
        combos = list(itertools.product(*[n.values for n in field_nodes]))
        assert len(node.result) == len(combos)
        for values, combo in zip(node.result, combos):
            field = tuple((n.axis.name, v) for n, v in zip(field_nodes, combo))
            points = out.setdefault(field, [])
            for (lat, lon), value in zip(node.coordinates, values):
                points.append((lat, lon, value))
    return out


def assert_same_records(reference, folded):
    assert list(reference) == list(folded)
    for field, points in reference.items():
        other = folded[field]
        assert len(points) == len(other), field
        for (lat_a, lon_a, val_a), (lat_b, lon_b, val_b) in zip(points, other):
            assert (lat_a, lon_a) == (lat_b, lon_b), field
            assert same_value(val_a, val_b), (field, lat_a, lon_a, val_a, val_b)


def filled_records(options, axes, request, bulk, **kwargs):
    datacube, tree = slice_tree(options, axes, request, bulk, **kwargs)
    datacube.get(tree)
    return datacube, tree, bulk_records(tree) if bulk else records(tree)


POLYGON_REQUEST = healpix_request([0, 0], [1, 1])  # replaced below, only the Selects are reused


def healpix_polygon_request(polygon):
    selects = [p for p in POLYGON_REQUEST.shapes if isinstance(p, Select)]
    return Request(*selects, Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], polygon)))


# ---------------------------------------------------------------------------------------------------------------------
# (a) the fold keeps the point order and values of the per-row path


@pytest.mark.parametrize("case", list(CASES))
def test_fold_matches_per_row_get(case):
    options, axes, request, _ = CASES[case]
    _, _, reference = filled_records(options, axes, request, bulk=False)
    _, tree, folded = filled_records(options, axes, request, bulk=True)
    assert all(isinstance(leaf, BulkGridTensorIndexNode) for leaf in tree.leaves)
    assert_same_records(reference, folded)


@pytest.mark.parametrize("case", ["regular_seam", "healpix_nested"])
def test_folded_values_decode_to_their_grid_index(case):
    options, axes, request, _ = CASES[case]
    _, tree, _ = filled_records(options, axes, request, bulk=True)
    for leaf in tree.leaves:
        for values in leaf.result:
            assert [index_of(v) for v in values] == leaf.indexes.tolist()


def test_fold_matches_per_row_get_on_merged_polygon_rows():
    request = healpix_polygon_request(EUROPE_POLYGON)
    _, _, reference = filled_records(HEALPIX_OPTIONS, None, request, bulk=False, merge_rows=True)
    _, tree, folded = filled_records(HEALPIX_OPTIONS, None, request, bulk=True, merge_rows=True)
    assert [leaf.point_count for leaf in tree.leaves] == [5017] * 4  # 2 params x 2 realizations
    assert_same_records(reference, folded)


def test_fold_matches_per_point_polygon_tree():
    """A polygon left uncompressed (one leaf per point) folds to the same ordered points."""
    request = healpix_polygon_request(EUROPE_POLYGON)
    _, _, reference = filled_records(HEALPIX_OPTIONS, None, request, bulk=False)
    _, _, folded = filled_records(HEALPIX_OPTIONS, None, request, bulk=True)
    assert_same_records(reference, folded)


def test_fold_keeps_bitmap_missing_points_and_missing_fields():
    options, axes, request, _ = CASES["regular_seam"]
    kwargs = dict(missing=[{"param": "165"}], nan_indices=range(0, 2000, 7))
    _, _, reference = filled_records(options, axes, request, bulk=False, **kwargs)
    _, _, folded = filled_records(options, axes, request, bulk=True, **kwargs)
    assert_same_records(reference, folded)


# ---------------------------------------------------------------------------------------------------------------------
# (b) the tree the fold leaves behind


def test_fold_is_idempotent_and_prepare_gives_the_get_coordinates():
    options, axes, request, _ = CASES["regular_overlap"]
    datacube, tree = slice_tree(options, axes, request, bulk=True)
    datacube.prepare(tree)
    (node,) = tree.leaves
    coordinates = node.coordinates.copy()
    indexes = node.indexes.copy()
    datacube.prepare(tree)
    (again,) = tree.leaves
    assert again is node
    assert np.array_equal(again.coordinates, coordinates)
    assert np.array_equal(again.indexes, indexes)
    datacube.get(tree)
    assert np.array_equal(node.coordinates, coordinates)
    assert [index_of(v) for v in node.result[0]] == indexes.tolist()


def test_fold_drops_duplicate_grid_points_where_they_were_first_seen():
    # a box from -9 to 360 degrees of longitude covers its first points twice
    options, axes = mars_options({"type": "regular", "resolution": 30}), MARS_AXES
    datacube, tree = slice_tree(options, axes, mars_request([0, -9], [7, 360]), bulk=True)
    sliced = sum(len(leaf.values) for leaf in tree.leaves)
    datacube.prepare(tree)
    (node,) = tree.leaves
    assert node.point_count < sliced
    assert len(set(node.indexes.tolist())) == node.point_count
    # the kept points are the first occurrence of each index in per-row order
    reference_datacube, reference_tree = slice_tree(options, axes, mars_request([0, -9], [7, 360]), bulk=False)
    reference_datacube.prepare(reference_tree)
    expected = [
        (leaf.parent.values[0], lon) for leaf in reference_tree.leaves for lon in np.asarray(leaf.values).tolist()
    ]
    assert [(lat, lon) for lat, lon in node.coordinates.tolist()] == expected


def test_rows_are_views_on_the_node_coordinates():
    options, axes, request, _ = CASES["healpix_nested"]
    datacube, tree = slice_tree(options, axes, request, bulk=True)
    datacube.prepare(tree)
    node = tree.leaves[0]
    assert len(node.lat_values) == len(node.lon_values)
    assert node.point_count == sum(len(lons) for lons in node.lon_values)
    for i, lons in enumerate(node.lon_values):
        assert np.shares_memory(lons, node.coordinates)
        assert np.array_equal(lons, node.coordinates[node.row_slice(i), 1])


def test_whole_field_ranges_replace_per_row_ranges():
    options, axes, request, _ = CASES["healpix_nested"]
    per_row, tree = slice_tree(options, axes, request, bulk=False)
    per_row.prepare(tree)
    bulk, bulk_tree = slice_tree(options, axes, request, bulk=True)
    bulk.prepare(bulk_tree)
    assert bulk.prototype_metrics["ranges_per_field"] < per_row.prototype_metrics["ranges_per_field"]
    expected = 0
    for node in bulk_tree.leaves:
        sorted_indexes = np.sort(node.indexes)
        expected += 1 + int(np.count_nonzero(np.diff(sorted_indexes) > 1))
    assert bulk.prototype_metrics["ranges_per_field"] == expected


def test_fold_leaves_no_python_object_per_point():
    """The fold allocates arrays, not one Python object per point."""
    import gc

    options, axes, request, _ = CASES["healpix_nested"]
    datacube, tree = slice_tree(options, axes, request, bulk=True)
    gc.collect()
    before = len(gc.get_objects())
    datacube.prepare(tree)
    gc.collect()
    grown = len(gc.get_objects()) - before
    points = sum(leaf.point_count for leaf in tree.leaves)
    assert points > 1000
    assert grown < points / 10, grown


# ---------------------------------------------------------------------------------------------------------------------
# (c) assignment, get_iter and prune on a folded tree


@pytest.mark.parametrize("case", list(CASES))
def test_get_iter_gives_one_entry_per_bulk_node(case):
    options, axes, request, _ = CASES[case]
    datacube, tree = slice_tree(options, axes, request, bulk=True)
    datacube.prepare(tree)
    streamed = tree.prune()
    positions = {id(node): i for i, node in enumerate(streamed.leaves)}
    fields = {}
    for path, leaf_values in datacube.get_iter(streamed):
        assert leaf_values is not None
        assert len(leaf_values) == 1
        node, values = leaf_values[0]
        assert isinstance(node, BulkGridTensorIndexNode)
        assert values.dtype == np.float64 and len(values) == node.point_count
        fields.setdefault(positions[id(node)], []).append(values)
    # the same values get() writes into the nodes, in the same order
    datacube.get(tree)
    for i, node in enumerate(tree.leaves):
        assert len(fields[i]) == len(node.result)
        for got, want in zip(fields[i], node.result):
            np.testing.assert_array_equal(got, np.asarray(want, dtype=np.float64))


def test_get_iter_reports_a_missing_field_as_none():
    options, axes, request, _ = CASES["regular_seam"]
    datacube, tree = slice_tree(options, axes, request, bulk=True, missing=[{"param": "165"}])
    missing = [path for path, values in datacube.get_iter(tree) if values is None]
    assert missing and all(path["param"] == "165" for path in missing)


def test_prune_shares_the_bulk_arrays_and_fills_independently():
    options, axes, request, select_axes = CASES["regular_seam"]
    datacube, tree = slice_tree(options, axes, request, bulk=True)
    datacube.prepare(tree)
    (node,) = tree.leaves
    sub = tree.prune(select={"param": "167", "step": 0, "number": 1})
    (pruned_node,) = sub.leaves
    assert pruned_node is not node
    assert pruned_node.coordinates is node.coordinates
    assert pruned_node.indexes is node.indexes
    assert pruned_node.tag_ids is node.tag_ids
    assert pruned_node.result == []
    datacube.get(sub)
    assert len(pruned_node.result) == 1
    assert node.result == []
    assert [index_of(v) for v in pruned_node.result[0]] == node.indexes.tolist()


def test_latitude_bands_are_refused_on_a_folded_tree():
    options, axes, request, _ = CASES["regular_seam"]
    datacube, tree = slice_tree(options, axes, request, bulk=True)
    datacube.prepare(tree)
    with pytest.raises(ValueError, match="bulk"):
        tree.latitude_point_counts()
    with pytest.raises(ValueError, match="bulk"):
        tree.prune(latitude_range=(0, 1))
    with pytest.raises(ValueError, match="bulk"):
        datacube.get(tree, latitude_range=(0, 1))


def test_latitude_bands_still_work_with_the_fold_off():
    options, axes, request, _ = CASES["regular_seam"]
    datacube, tree = slice_tree(options, axes, request, bulk=False)
    counts = datacube.prepare(tree).latitude_point_counts()
    assert len(counts) > 1
    band = tree.prune(latitude_range=(0, 1))
    assert sum(len(leaf.values) for leaf in band.leaves) == counts[0]
