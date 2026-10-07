"""The flat (``values_flat``) assignment of gribjump results, and ``FDBDatacube.get_iter``.

Every scenario is fetched twice -- once with the per-range implementation this branch replaced
(``tests/legacy_assign.py``) and once with the flat one -- and the two trees must be identical.  ``get_iter`` is
checked against ``get`` on the same scenarios.
"""

import itertools

import numpy as np
import pytest
from fake_gribjump import index_of
from legacy_assign import use_legacy_assignment
from test_polygon_rows import CASES as POLYGON_CASES
from test_polygon_rows import slice_polygon
from test_pruned_get import CASES, axis_values, iter_nodes, make_tree, records, snapshot

import polytope_feature.datacube.backends.fdb as fdb_module
from polytope_feature.shapes import Polygon, Union

# ---------------------------------------------------------------------------------------------------------------------
# Helpers


def leaves_of(tree):
    return [node for node, _ in iter_nodes(tree) if node is not tree and len(node.children) == 0]


def legacy_tree(make, monkeypatch, fetch):
    """``fetch`` a freshly sliced tree with the per-range assignment, in an isolated monkeypatch context."""
    with monkeypatch.context() as patch:
        use_legacy_assignment(patch)
        datacube, tree = make()
        return fetch(datacube, tree)


def full_get(datacube, tree):
    return datacube.get(tree)


def banded_get(select_axes, band_size=2):
    """Fetch every (select combination) x (latitude band) sub-tree of a prepared tree, returning the sub-trees."""

    def fetch(datacube, tree):
        prepared = datacube.prepare(tree)
        out = []
        value_lists = [axis_values(prepared, axis) for axis in select_axes]
        for combo in itertools.product(*value_lists):
            select = dict(zip(select_axes, combo))
            counts = prepared.latitude_point_counts(select)
            for start in range(0, len(counts), band_size):
                band = (start, min(start + band_size, len(counts)))
                out.append(datacube.get(prepared, select=select, latitude_range=band))
        return out

    return fetch


def assert_same_snapshot(got, expected):
    """Compare tree snapshots, counting NaN results (bitmap-missing points) as equal."""
    assert len(got) == len(expected)
    for a, b in zip(got, expected):
        assert a[:3] == b[:3] and a[4] == b[4]
        assert len(a[3]) == len(b[3])
        for x, y in zip(a[3], b[3]):
            assert x is y or x == y or (isinstance(x, float) and isinstance(y, float) and np.isnan(x) and np.isnan(y))


# ---------------------------------------------------------------------------------------------------------------------
# (a) the flat path writes exactly what the per-range path wrote


@pytest.mark.parametrize(
    "missing, nan_indices",
    [
        (None, None),
        ([{"param": "165", "step": "6"}], None),
        ([{"param": "165"}], None),
        (None, set(range(0, 20_000, 7))),
    ],
)
@pytest.mark.parametrize("case", list(CASES))
def test_flat_assignment_matches_per_range_assignment(case, missing, nan_indices, monkeypatch):
    def make():
        datacube, tree, _, _ = make_tree(case, missing=missing, nan_indices=nan_indices)
        return datacube, tree

    before = legacy_tree(make, monkeypatch, full_get)
    datacube, tree = make()
    after = datacube.get(tree)
    assert_same_snapshot(snapshot(after), snapshot(before))
    # the values really are the ones the coordinates ask for
    mapper = datacube.grid_transformation
    for points in records(after).values():
        for lat, lon, value in points:
            if value is not None and not np.isnan(value):
                assert index_of(value) == mapper.unmap((lat,), [lon])[0]


@pytest.mark.parametrize("case", list(CASES))
def test_flat_assignment_matches_per_range_assignment_in_bands(case, monkeypatch):
    select_axes = CASES[case][3]

    def make():
        datacube, tree, _, _ = make_tree(case, missing=[{"param": "165", "step": "6"}])
        return datacube, tree

    before = legacy_tree(make, monkeypatch, banded_get(select_axes))
    datacube, tree = make()
    after = banded_get(select_axes)(datacube, tree)
    assert len(after) == len(before)
    for got, expected in zip(after, before):
        assert_same_snapshot(snapshot(got), snapshot(expected))


@pytest.mark.parametrize("case", list(POLYGON_CASES))
@pytest.mark.parametrize("overlapping", [False, True])
def test_flat_assignment_matches_per_range_assignment_for_merged_polygon_rows(case, overlapping, monkeypatch):
    points = POLYGON_CASES[case][3]
    shapes = None
    if overlapping:
        # two polygons of one union: the rows hold duplicate points and keep their value order
        shifted = [[p[0] + (points[1][0] - points[0][0] + 1) / 3, p[1]] for p in points]
        shapes = [Union(["latitude", "longitude"], *(Polygon(["latitude", "longitude"], p) for p in (points, shifted)))]

    def make():
        datacube, tree, _ = slice_polygon(case, merge_rows=True, shapes=shapes)
        return datacube, tree

    before = legacy_tree(make, monkeypatch, full_get)
    datacube, tree = make()
    assert_same_snapshot(snapshot(datacube.get(tree)), snapshot(before))


def test_results_are_read_only_from_the_flat_buffer(monkeypatch):
    """The per-range ``values`` list is never built: it is one numpy object per range."""

    def forbidden(self):
        raise AssertionError("assignment must not use the per-range values list")

    monkeypatch.setattr("fake_gribjump._ExtractResult.values", property(forbidden))
    datacube, tree, _, _ = make_tree("healpix_nested")
    filled = datacube.get(tree)
    assert all(leaf.result.dtype == np.float64 for leaf in leaves_of(filled))


def test_leaf_result_is_one_float64_array_for_all_fields():
    datacube, tree, _, _ = make_tree("regular_seam")
    filled = datacube.get(tree)
    n_fields = 2 * 2 * 2  # param x step x number, all compressed
    for leaf in leaves_of(filled):
        assert leaf.result.dtype == np.float64
        assert leaf.result.flags.c_contiguous
        assert len(leaf.result) == len(leaf.values) * n_fields


def test_short_field_result_is_rejected(monkeypatch):
    datacube, tree, _, _ = make_tree("regular_seam")
    original = fdb_module.field_values_flat

    def truncated(result):
        flat = original(result)
        return None if flat is None else flat[:-1]

    monkeypatch.setattr(fdb_module, "field_values_flat", truncated)
    with pytest.raises(ValueError, match="values for a field"):
        datacube.get(tree)


# ---------------------------------------------------------------------------------------------------------------------
# (b) get_iter


def consume_get_iter(datacube, tree, **kwargs):
    """``{id(leaf): (leaf, [values of each field present])}`` and the paths yielded as missing."""
    blocks = {}
    missing_paths = []
    for path, leaf_values in datacube.get_iter(tree, **kwargs):
        assert isinstance(path, dict) and all(isinstance(v, str) for v in path.values())
        if leaf_values is None:
            missing_paths.append(path)
            continue
        for leaf, values in leaf_values:
            assert values.dtype == np.float64 and len(values) == len(leaf.values)
            blocks.setdefault(id(leaf), (leaf, []))[1].append(values)
    return blocks, missing_paths


def present_blocks(leaf, n_points):
    """The field blocks of a filled leaf's result that gribjump had data for, as float64 arrays."""
    values = leaf.result_array()
    out = []
    for start in range(0, len(values), n_points):
        block = leaf.result[start : start + n_points]  # noqa: E203
        if not all(v is None for v in block):
            out.append(values[start : start + n_points])  # noqa: E203
    return out


def assert_get_iter_matches_get(case, missing=None, nan_indices=None, **kwargs):
    datacube, tree, _, _ = make_tree(case, missing=missing, nan_indices=nan_indices)
    filled = datacube.get(tree.prune(), **kwargs)
    datacube2, tree2, _, gj = make_tree(case, missing=missing, nan_indices=nan_indices)
    blocks, missing_paths = consume_get_iter(datacube2, tree2, **kwargs)

    expected_leaves = leaves_of(filled)
    assert len(blocks) == len(expected_leaves)
    for (_, arrays), leaf in zip(blocks.values(), expected_leaves):
        n_points = len(leaf.values)
        expected = present_blocks(leaf, n_points)
        assert len(arrays) == len(expected)
        for got, want in zip(arrays, expected):
            np.testing.assert_array_equal(got, want)
    # one item per gribjump request, missing where the fake has no field for the path
    requested = gj.extract_calls[-1]
    assert len(missing_paths) == sum(1 for request in requested if gj._is_missing(request[0]))
    assert [dict(path) for path in missing_paths] == [r[0] for r in requested if gj._is_missing(r[0])]
    return filled


@pytest.mark.parametrize("case", list(CASES))
def test_get_iter_gives_the_values_of_get(case):
    assert_get_iter_matches_get(case)
    assert_get_iter_matches_get(case, nan_indices=set(range(0, 20_000, 7)))


@pytest.mark.parametrize("case", list(CASES))
def test_get_iter_reports_missing_fields_as_none(case):
    datacube, tree, _, _ = make_tree(case, missing=[{"param": "165"}])
    paths = [path for path, values in datacube.get_iter(tree) if values is None]
    assert paths and all(path["param"] == "165" for path in paths)
    assert_get_iter_matches_get(case, missing=[{"param": "165", "step": "6"}])


def test_get_iter_with_select_and_latitude_range():
    select = {"param": "167", "step": 6, "number": 2}
    assert_get_iter_matches_get("regular_overlap", select=select, latitude_range=(1, 3))


def test_get_iter_fields_come_in_the_product_order_of_the_compressed_axes():
    datacube, tree, _, _ = make_tree("regular_seam")
    paths = [path for path, _ in datacube.get_iter(tree)]
    keys = [key for key in paths[0] if len({path[key] for path in paths}) > 1]
    assert keys == ["param", "step", "number"]  # tree order, outermost first
    assert [tuple(path[key] for key in keys) for path in paths] == list(
        itertools.product(["165", "167"], ["0", "6"], ["1", "2"])
    )


def test_get_iter_leaves_the_tree_prepared_and_unfilled():
    datacube, tree, _, _ = make_tree("healpix_nested")
    prepared = datacube.prepare(tree.prune())
    fetched = tree.prune()
    consumed = list(datacube.get_iter(fetched))
    assert len(consumed) == 2 * 2  # param x realization, neither compressed: one request each
    assert all(len(leaf.result) == 0 for leaf in leaves_of(fetched))
    assert snapshot(fetched) == snapshot(prepared)


def test_get_iter_of_an_empty_tree_yields_nothing():
    datacube, tree, _, _ = make_tree("regular_seam")
    empty = tree.prune(latitude_range=(100, 200))
    assert list(datacube.get_iter(empty)) == []


def test_get_iter_requests_nothing_before_the_first_item():
    datacube, tree, _, gj = make_tree("regular_seam")
    iterator = datacube.get_iter(tree)
    assert gj.extract_calls == []
    next(iterator)
    assert len(gj.extract_calls) == 1
