"""The ``bulk_grid_leaves`` fold of a structured tree: same points, same order, same values.

Drives the real ``FDBDatacube`` against the in-memory fake gribjump (``tests/fake_gribjump.py``) with
the fold off and on and compares the ordered ``(latitude, longitude)`` list and the per-field values,
which is what makes the CovJSON bytes of the two paths identical.
"""

import numpy as np
import pytest
from fake_gribjump import GribJump, index_of
from test_pruned_get import (
    CASES,
    HEALPIX_OPTIONS,
    MARS_AXES,
    healpix_request,
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


def slice_tree(options, axes, request, merge_rows=False, missing=None, nan_indices=None):
    gj = GribJump(axes or {}, missing=missing, nan_indices=nan_indices)
    api = Polytope(datacube=gj, options=options)
    api._merge_union_rows = merge_rows
    api.datacube.check_branching_axes(request)
    api.switch_polytope_dim(request)
    api.datacube.nearest_search = {}
    tree = api.slice(api.datacube, request.polytopes())
    return api.datacube, tree


def expected_points(datacube, tree):
    """The points the fold has to produce for a sliced (unfolded) ``tree``.

    The rule the CovJSON bytes rest on: the rows in tree order, each row's points in grid-index order --
    except a merged polygon row, whose values stay ascending (``_keep_value_order``) -- and the first
    occurrence of a grid index wins when a row covers a point twice.
    """
    mapper = datacube.grid_transformation
    seen, out = set(), []
    for leaf in tree.leaves:
        lat = leaf.parent.values[0]
        lons = np.asarray(leaf.values, dtype=np.float64).tolist()
        indexes = [mapper.unmap((lat,), [lon])[0] for lon in lons]
        order = range(len(lons)) if leaf._keep_value_order else np.argsort(indexes, kind="stable")
        for i in order:
            if indexes[i] in seen:
                continue
            seen.add(indexes[i])
            out.append((lat, lons[i]))
    return out


def assert_same_records(reference, folded):
    assert list(reference) == list(folded)
    for field, points in reference.items():
        other = folded[field]
        assert len(points) == len(other), field
        for (lat_a, lon_a, val_a), (lat_b, lon_b, val_b) in zip(points, other):
            assert (lat_a, lon_a) == (lat_b, lon_b), field
            assert same_value(val_a, val_b), (field, lat_a, lon_a, val_a, val_b)


def filled_records(options, axes, request, **kwargs):
    datacube, tree = slice_tree(options, axes, request, **kwargs)
    datacube.get(tree)
    return datacube, tree, records(tree)


POLYGON_REQUEST = healpix_request([0, 0], [1, 1])  # replaced below, only the Selects are reused


def healpix_polygon_request(polygon):
    selects = [p for p in POLYGON_REQUEST.shapes if isinstance(p, Select)]
    return Request(*selects, Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], polygon)))


# ---------------------------------------------------------------------------------------------------------------------
# (a) the fold keeps the points of the sliced rows, in order, with their own values


@pytest.mark.parametrize("case", list(CASES))
def test_folded_points_are_the_sliced_rows_in_order(case):
    options, axes, request, _ = CASES[case]
    datacube, sliced = slice_tree(options, axes, request)
    expected = expected_points(datacube, sliced)
    datacube, tree, folded = filled_records(options, axes, request)
    assert all(isinstance(leaf, BulkGridTensorIndexNode) for leaf in tree.leaves)
    mapper = datacube.grid_transformation
    for points in folded.values():
        assert [(lat, lon) for lat, lon, _ in points] == expected
        for lat, lon, value in points:
            # the fake encodes the grid index of the point it belongs to in every value
            assert index_of(value) == mapper.unmap((lat,), [lon])[0]


@pytest.mark.parametrize("case", ["regular_seam", "healpix_nested"])
def test_folded_values_decode_to_their_grid_index(case):
    options, axes, request, _ = CASES[case]
    _, tree, _ = filled_records(options, axes, request)
    for leaf in tree.leaves:
        for values in leaf.result:
            assert [index_of(v) for v in values] == leaf.indexes.tolist()


@pytest.mark.parametrize("merge_rows", [False, True], ids=["per-point", "merged-rows"])
def test_a_polygon_folds_to_its_sliced_points(merge_rows):
    """A polygon sliced into one leaf per point, or one array leaf per row, folds to the same points."""
    request = healpix_polygon_request(EUROPE_POLYGON)
    datacube, sliced = slice_tree(HEALPIX_OPTIONS, None, request, merge_rows=merge_rows)
    expected = expected_points(datacube, sliced) if merge_rows else None
    _, tree, folded = filled_records(HEALPIX_OPTIONS, None, request, merge_rows=merge_rows)
    assert [leaf.point_count for leaf in tree.leaves] == [5017] * 4  # 2 params x 2 realizations
    mapper = datacube.grid_transformation
    for points in folded.values():
        if expected is not None:
            assert [(lat, lon) for lat, lon, _ in points] == expected
        for lat, lon, value in points:
            assert index_of(value) == mapper.unmap((lat,), [lon])[0]


def test_fold_keeps_bitmap_missing_points_and_missing_fields():
    options, axes, request, _ = CASES["regular_seam"]
    datacube, probe = slice_tree(options, axes, request)
    datacube.prepare(probe)
    indexes = sorted({int(i) for node in probe.leaves for i in node.indexes})
    nan_indices = set(indexes[::7])
    datacube, _, folded = filled_records(options, axes, request, missing=[{"param": "165"}], nan_indices=nan_indices)
    mapper = datacube.grid_transformation
    n_nan = 0
    for field, points in folded.items():
        if dict(field)["param"] == "165":
            assert all(value is None for _, _, value in points)
            continue
        for lat, lon, value in points:
            index = mapper.unmap((lat,), [lon])[0]
            if index in nan_indices:
                assert np.isnan(value)
                n_nan += 1
            else:
                assert index_of(value) == index
    assert n_nan > 0


# ---------------------------------------------------------------------------------------------------------------------
# (b) the tree the fold leaves behind


def test_fold_is_idempotent_and_prepare_gives_the_get_coordinates():
    options, axes, request, _ = CASES["regular_overlap"]
    datacube, tree = slice_tree(options, axes, request)
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
    datacube, tree = slice_tree(options, axes, mars_request([0, -9], [7, 360]))
    points = [(leaf.parent.values[0], lon) for leaf in tree.leaves for lon in leaf.values.tolist()]
    expected = expected_points(datacube, tree)
    assert len(expected) < len(points)
    datacube.prepare(tree)
    (node,) = tree.leaves
    assert node.point_count == len(expected)
    assert len(set(node.indexes.tolist())) == node.point_count
    # the kept points are the first occurrence of each index in per-row order
    assert [(lat, lon) for lat, lon in node.coordinates.tolist()] == expected


def test_rows_are_views_on_the_node_coordinates():
    options, axes, request, _ = CASES["healpix_nested"]
    datacube, tree = slice_tree(options, axes, request)
    datacube.prepare(tree)
    node = tree.leaves[0]
    assert len(node.lat_values) == len(node.lon_values)
    assert node.point_count == sum(len(lons) for lons in node.lon_values)
    for i, lons in enumerate(node.lon_values):
        assert np.shares_memory(lons, node.coordinates)
        assert np.array_equal(lons, node.coordinates[node.row_slice(i), 1])


def test_ranges_are_the_gaps_in_the_whole_fields_indexes():
    """One range per gap in a field's sorted indexes, instead of one per row (or per point on HEALPix)."""
    options, axes, request, _ = CASES["healpix_nested"]
    datacube, tree = slice_tree(options, axes, request)
    datacube.prepare(tree)
    expected = 0
    points = 0
    for node in tree.leaves:
        sorted_indexes = np.sort(node.indexes)
        expected += 1 + int(np.count_nonzero(np.diff(sorted_indexes) > 1))
        points += node.point_count
    assert datacube.prototype_metrics["ranges_per_field"] == expected
    # a HEALPix box asks for one range per several points, where the per-row planning asked for
    # roughly one per point (the ring's pixels are scattered over the index space)
    assert expected < points / 2


def test_fold_leaves_no_python_object_per_point():
    """The fold allocates arrays, not one Python object per point."""
    import gc

    options, axes, request, _ = CASES["healpix_nested"]
    datacube, tree = slice_tree(options, axes, request)
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
    datacube, tree = slice_tree(options, axes, request)
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
    datacube, tree = slice_tree(options, axes, request, missing=[{"param": "165"}])
    missing = [path for path, values in datacube.get_iter(tree) if values is None]
    assert missing and all(path["param"] == "165" for path in missing)


def test_prune_shares_the_bulk_arrays_and_fills_independently():
    options, axes, request, select_axes = CASES["regular_seam"]
    datacube, tree = slice_tree(options, axes, request)
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


def test_spatial_axes_cannot_be_selected():
    """A spatial sub-tree is copied whole: there is no way to prune a field to part of its points."""
    options, axes, request, _ = CASES["regular_seam"]
    datacube, tree = slice_tree(options, axes, request)
    datacube.prepare(tree)
    with pytest.raises(ValueError, match="spatial axis 'latitude'"):
        tree.prune(select={"latitude": 0.0})
    with pytest.raises(ValueError, match="spatial axis 'longitude'"):
        datacube.get(tree, select={"longitude": 0.0})
