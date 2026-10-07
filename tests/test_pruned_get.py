"""FDBDatacube.get on pruned sub-trees, and numpy leaf values, driven by an in-memory fake gribjump."""

import itertools
import logging
import sys

import numpy as np
import pandas as pd
import pytest
from fake_gribjump import GribJump, index_of

from polytope_feature.datacube.backends.fdb import FDBDatacube
from polytope_feature.datacube.tensor_index_tree import TensorIndexTree
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select

# ---------------------------------------------------------------------------------------------------------------------
# Datacube configurations


def mars_options(mapper, extra_compressed=("number",)):
    return {
        "axis_config": [
            {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
            {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
            {
                "axis_name": "date",
                "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
            },
            {
                "axis_name": "values",
                "transformations": [dict(name="mapper", axes=["latitude", "longitude"], **mapper)],
            },
            {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
        ],
        "compressed_axes_config": [
            "longitude",
            "latitude",
            "levtype",
            "step",
            "date",
            "domain",
            "expver",
            "param",
            "class",
            "stream",
            "type",
        ]
        + list(extra_compressed),
        "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "enfo"},
    }


MARS_AXES = {
    "class": ["od"],
    "date": ["20240101"],
    "time": ["0000"],
    "domain": ["g"],
    "expver": ["0001"],
    "levtype": ["sfc"],
    "param": ["165", "167"],
    "step": ["0", "6"],
    "number": ["1", "2"],
    "stream": ["enfo"],
    "type": ["pf"],
}


def mars_request(box_lower, box_upper):
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
        Box(["latitude", "longitude"], box_lower, box_upper),
    )


# HEALPix nested configuration from tests/test_healpix_nested_grid.py (only latitude/longitude compressed, so the
# non-spatial axes branch instead of being compressed), with two params and two realizations.
HEALPIX_OPTIONS = {
    "axis_config": [
        {
            "axis_name": "date",
            "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        },
        {
            "axis_name": "values",
            "transformations": [
                {"name": "mapper", "type": "healpix_nested", "resolution": 128, "axes": ["latitude", "longitude"]}
            ],
        },
        {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
        {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
    ],
    "pre_path": {"class": "d1", "expver": "0001", "levtype": "sfc", "stream": "clte"},
    "compressed_axes_config": ["longitude", "latitude"],
    "alternative_axes": [
        {"axis_name": "class", "values": ["d1"]},
        {"axis_name": "activity", "values": ["ScenarioMIP"]},
        {"axis_name": "dataset", "values": ["climate-dt"]},
        {"axis_name": "date", "values": ["20200102"]},
        {"axis_name": "time", "values": ["0100"]},
        {"axis_name": "experiment", "values": ["SSP3-7.0"]},
        {"axis_name": "expver", "values": ["0001"]},
        {"axis_name": "generation", "values": ["1"]},
        {"axis_name": "levtype", "values": ["sfc"]},
        {"axis_name": "model", "values": ["IFS-NEMO"]},
        {"axis_name": "param", "values": ["165", "167"]},
        {"axis_name": "realization", "values": ["1", "2"]},
        {"axis_name": "resolution", "values": ["standard"]},
        {"axis_name": "stream", "values": ["clte"]},
        {"axis_name": "type", "values": ["fc"]},
    ],
}


def healpix_request(box_lower, box_upper):
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
        Box(["latitude", "longitude"], box_lower, box_upper),
    )


# (id, options, gribjump axes, request, axes to select on)
CASES = {
    "regular_seam": (
        mars_options({"type": "regular", "resolution": 30}),
        MARS_AXES,
        mars_request([-12, -10], [12, 10]),
        ["param", "step", "number"],
    ),
    "regular_full_circle": (
        mars_options({"type": "regular", "resolution": 30}),
        MARS_AXES,
        mars_request([0, 0], [7, 360]),
        ["param", "step", "number"],
    ),
    # overlapping longitudes: leaves hold duplicate points that get() de-duplicates
    "regular_overlap": (
        mars_options({"type": "regular", "resolution": 30}),
        MARS_AXES,
        mars_request([0, -9], [7, 360]),
        ["param", "step", "number"],
    ),
    "healpix_nested": (
        HEALPIX_OPTIONS,
        None,
        healpix_request([-3, 350], [3, 365]),
        ["param", "realization"],
    ),
    "octahedral": (
        mars_options({"type": "octahedral", "resolution": 1280}),
        MARS_AXES,
        mars_request([0, 359.8], [0.4, 360.3]),
        ["param", "step", "number"],
    ),
}


# ---------------------------------------------------------------------------------------------------------------------
# Helpers


def slice_request(options, axes, request, missing=None, nan_indices=None):
    gj = GribJump(axes or {}, missing=missing, nan_indices=nan_indices)
    api = Polytope(datacube=gj, options=options)
    datacube = api.datacube
    assert isinstance(datacube, FDBDatacube)
    datacube.check_branching_axes(request)
    tree = api.slice(datacube, request.polytopes())
    return datacube, tree, gj


def make_tree(case, missing=None, nan_indices=None):
    options, axes, request, select_axes = CASES[case]
    datacube, tree, gj = slice_request(options, axes, request, missing, nan_indices)
    return datacube, tree, select_axes, gj


def iter_nodes(node, path: tuple = ()):
    """Yield (node, ancestors) depth-first in traversal order."""
    yield node, path
    for child in node.children:
        yield from iter_nodes(child, path + (child,))


def records(tree):
    """Expand a filled tree into {field: [(lat, lon, value), ...]} in traversal order.

    ``field`` is the tuple of (axis, value) pairs of the non-spatial axes, following the itertools.product layout
    of a compressed leaf's ``result``.
    """
    out = {}
    for node, ancestors in iter_nodes(tree):
        if len(node.children) != 0 or node is tree:
            continue
        *field_nodes, lat_node, _ = ancestors
        assert isinstance(node.values, np.ndarray) and node.values.dtype == np.float64
        assert isinstance(node.result, np.ndarray)
        n = len(node.values)
        combos = list(itertools.product(*[n_.values for n_ in field_nodes]))
        assert len(node.result) == n * len(combos)
        for c, combo in enumerate(combos):
            field = tuple((n_.axis.name, v) for n_, v in zip(field_nodes, combo))
            for p in range(n):
                out.setdefault(field, []).append((lat_node.values[0], node.values[p], node.result[c * n + p]))
    return out


def snapshot(tree):
    """Structure, values and results of a tree, for checking that it was not mutated."""
    snap = []
    for node, ancestors in iter_nodes(tree):
        values = tuple(node.values.tolist()) if isinstance(node.values, np.ndarray) else node.values
        result = tuple(node.result.tolist()) if isinstance(node.result, np.ndarray) else tuple(node.result)
        snap.append((len(ancestors), node.axis.name, values, result, len(node.children)))
    return snap


def same_value(a, b):
    if a is None or b is None:
        return a is b
    return a == b or (np.isnan(a) and np.isnan(b))


def assert_same_records(full, banded):
    assert list(full) == list(banded)
    for field, points in full.items():
        other = banded[field]
        assert len(points) == len(other), field
        for (lat_a, lon_a, val_a), (lat_b, lon_b, val_b) in zip(points, other):
            assert (lat_a, lon_a) == (lat_b, lon_b)
            assert same_value(val_a, val_b), (field, lat_a, lon_a, val_a, val_b)


def axis_values(tree, axis):
    vals = []
    for node, _ in iter_nodes(tree):
        if node is not tree and node.axis.name == axis:
            for v in node.values:
                if v not in vals:
                    vals.append(v)
    return vals


def banded_records(datacube, tree, select_axes, band_size):
    """Fetch every (select combination) x (latitude band) sub-tree and concatenate the results per field."""
    out = {}
    value_lists = [axis_values(tree, a) for a in select_axes]
    for combo in itertools.product(*value_lists):
        select = dict(zip(select_axes, combo))
        counts = tree.latitude_point_counts(select)
        assert len(counts) > 1
        for start in range(0, len(counts), band_size):
            band = (start, min(start + band_size, len(counts)))
            sub = tree.prune(select=select, latitude_range=band)
            assert sum(len(leaf.values) for leaf in sub.leaves) == sum(counts[band[0] : band[1]])
            filled = datacube.get(sub)
            assert filled is sub
            for field, points in records(sub).items():
                out.setdefault(field, []).extend(points)
    return out


def full_records(datacube, tree):
    full = tree.prune()  # independent copy: get mutates the tree it fills
    datacube.get(full)
    return full, records(full)


# ---------------------------------------------------------------------------------------------------------------------
# (a) full get == concatenation of pruned gets


@pytest.mark.parametrize("case", list(CASES))
@pytest.mark.parametrize("band_size", [1, 2])
def test_pruned_gets_reproduce_full_get(case, band_size):
    datacube, tree, select_axes, _ = make_tree(case)
    before = snapshot(tree)
    _, full = full_records(datacube, tree)
    assert snapshot(tree) == before

    # values line up with coordinates: the fake encodes the grid index in each value
    mapper = datacube.grid_transformation
    for points in full.values():
        for lat, lon, value in points:
            assert index_of(value) == mapper.unmap((lat,), [lon])[0]

    if case == "regular_overlap":
        assert sum(len(points) for points in full.values()) < sum(tree.latitude_point_counts()) * len(full)
    banded = banded_records(datacube, tree, select_axes, band_size)
    assert_same_records(full, banded)
    # sequential pruned gets never touch the parent tree
    assert snapshot(tree) == before


def test_get_with_select_and_latitude_range_prunes_internally():
    datacube, tree, _, gj = make_tree("regular_seam")
    before = snapshot(tree)
    counts = tree.latitude_point_counts({"param": "167", "step": 6, "number": 2})
    sub = datacube.get(tree, select={"param": "167", "step": 6, "number": 2}, latitude_range=(1, 3))
    assert snapshot(tree) == before
    assert sub is not tree
    assert sum(len(leaf.result) for leaf in sub.leaves) == sum(counts[1:3])
    fields = records(sub)
    assert list(fields) == [
        (
            ("class", "od"),
            ("date", np.datetime64("2024-01-01T00:00:00")),
            ("domain", "g"),
            ("expver", "0001"),
            ("levtype", "sfc"),
            ("param", "167"),
            ("step", 6),
            ("number", 2),
            ("stream", "enfo"),
            ("type", "pf"),
        )
    ]
    # only the selected field was requested from gribjump
    (requests,) = gj.extract_calls
    assert [r[0]["param"] for r in requests] == ["167"] * len(requests)
    assert {(r[0]["step"], r[0]["number"]) for r in requests} == {("6", "2")}


def test_get_does_not_depend_on_previous_unmapping_state():
    datacube, tree, _, _ = make_tree("regular_seam")
    datacube.unwanted_path = {"latitude": (123.0,)}
    _, full = full_records(datacube, tree)
    datacube2, tree2, _, _ = make_tree("regular_seam")
    _, full2 = full_records(datacube2, tree2)
    assert_same_records(full, full2)


# ---------------------------------------------------------------------------------------------------------------------
# (b) pruning to a value that is not in the tree


def test_prune_to_absent_value_raises():
    _, tree, _, _ = make_tree("regular_seam")
    with pytest.raises(ValueError, match="param"):
        tree.prune(select={"param": "999"})
    with pytest.raises(ValueError, match="step"):
        tree.prune(select={"param": "167", "step": 12})
    with pytest.raises(ValueError, match="levelist"):
        tree.prune(select={"levelist": 500})
    with pytest.raises(ValueError):
        tree.latitude_point_counts({"param": "999"})


def test_prune_rejects_spatial_select_and_non_root():
    _, tree, _, _ = make_tree("regular_seam")
    with pytest.raises(ValueError):
        tree.prune(select={"latitude": 0.0})
    with pytest.raises(ValueError):
        tree.children[0].prune()
    with pytest.raises(ValueError):
        tree.prune(latitude_range=(3, 1))


def test_prune_band_partition_and_empty_band():
    _, tree, _, _ = make_tree("regular_seam")
    counts = tree.latitude_point_counts()
    total = sum(len(leaf.values) for leaf in tree.leaves)
    assert sum(counts) == total
    assert len(tree.prune(latitude_range=(len(counts), len(counts) + 5)).children) == 0
    lats = [n.values[0] for n, _ in iter_nodes(tree) if n is not tree and n.axis.name == "latitude"]
    band = tree.prune(latitude_range=(1, 3))
    band_lats = [n.values[0] for n, _ in iter_nodes(band) if n is not band and n.axis.name == "latitude"]
    assert band_lats == lats[1:3]


# ---------------------------------------------------------------------------------------------------------------------
# (c) numpy leaf values through the tree API


def test_numpy_leaf_values_survive_tree_operations():
    datacube, tree_a, _, _ = make_tree("regular_seam")
    for leaf in tree_a.leaves:
        assert isinstance(leaf.values, np.ndarray) and leaf.values.dtype == np.float64
        assert np.all(np.diff(leaf.values) >= 0)
        assert isinstance(leaf.flatten()["longitude"], np.ndarray)
        assert isinstance(leaf.flatten()["latitude"], tuple)
    # non-leaf nodes keep hashable tuples
    for node, _ in iter_nodes(tree_a):
        if len(node.children) != 0:
            assert isinstance(node.values, tuple)
            hash(node)

    # merge: identical trees merge into one; a disjoint box adds latitude nodes
    _, tree_b, _, _ = make_tree("regular_seam")
    n_leaves = len(tree_a.leaves)
    tree_a.merge(tree_b)
    assert len(tree_a.leaves) == n_leaves
    _, tree_c, _ = slice_request(CASES["regular_seam"][0], MARS_AXES, mars_request([30, 0], [36, 10]))
    tree_a.merge(tree_c)
    leaves = tree_a.leaves
    assert len(leaves) == n_leaves + len(tree_c.leaves)
    assert all(isinstance(leaf.values, np.ndarray) for leaf in leaves)
    lat_nodes = [n for n, _ in iter_nodes(tree_a) if n is not tree_a and n.axis.name == "latitude"]
    assert [n.values for n in lat_nodes] == sorted(n.values for n in lat_nodes)

    # find_child / equality with numpy values (within tolerance)
    leaf = leaves[0]
    probe = TensorIndexTree(leaf.axis, leaf.values - 1e-13)
    assert leaf.parent.find_child(probe) is leaf
    assert TensorIndexTree(leaf.axis, tuple(leaf.values.tolist())) == leaf
    assert hash(TensorIndexTree(leaf.axis, tuple(leaf.values.tolist()))) == hash(leaf)

    # remove_branch
    lat = leaf.parent
    leaf.remove_branch()
    assert lat.parent is None or lat not in lat.parent.children
    assert len(tree_a.leaves) == len(leaves) - 1

    # remove_compressed_branch keeps an array
    leaf2 = tree_a.leaves[0]
    first = leaf2.values[0]
    leaf2.remove_compressed_branch(first)
    assert isinstance(leaf2.values, np.ndarray) and first not in leaf2.values

    # pprint, including results after get
    datacube.get(tree_b)
    lines = []
    handler = logging.Handler(logging.DEBUG)
    handler.emit = lambda record: lines.append(record.getMessage())
    root = logging.getLogger()
    old_level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        tree_b.pprint()
    finally:
        root.removeHandler(handler)
        root.setLevel(old_level)
    assert any("longitude=[" in line for line in lines)


# ---------------------------------------------------------------------------------------------------------------------
# (d) missing fields and bitmap-missing points


@pytest.mark.parametrize("case", ["regular_seam", "octahedral"])
def test_missing_field_matches_full_get(case):
    missing = [{"param": "165", "step": "6"}]
    datacube, tree, select_axes, _ = make_tree(case, missing=missing)
    full_tree, full = full_records(datacube, tree)
    for field, points in full.items():
        f = dict(field)
        values = [v for _, _, v in points]
        if f["param"] == "165" and f["step"] == 6:
            assert all(v is None for v in values)
        else:
            assert all(v is not None for v in values)
    for leaf in full_tree.leaves:
        assert leaf.result.dtype == object
        arr = leaf.result_array()
        assert arr.dtype == np.float64 and np.isnan(arr).sum() == sum(v is None for v in leaf.result)

    banded = banded_records(datacube, tree, select_axes, band_size=2)
    assert_same_records(full, banded)

    sub = datacube.get(tree, select={"param": "165", "step": 6, "number": 1})
    for leaf in sub.leaves:
        assert all(v is None for v in leaf.result)
        assert np.all(np.isnan(leaf.result_array()))
    sub = datacube.get(tree, select={"param": "167", "step": 6, "number": 1})
    for leaf in sub.leaves:
        assert leaf.result.dtype == np.float64


def test_missing_field_on_split_ranges_gives_one_none_per_point():
    # the seam box splits each latitude line into two index ranges
    datacube, tree, _, _ = make_tree("regular_seam", missing=[{"param": "165"}])
    sub = datacube.get(tree, select={"param": "165", "step": 0, "number": 1})
    for leaf in sub.leaves:
        assert len(leaf.result) == len(leaf.values)
        assert all(v is None for v in leaf.result)


def test_bitmap_missing_points_are_nan_in_full_and_banded():
    datacube, tree, select_axes, _ = make_tree("regular_seam", nan_indices=set(range(0, 10_000, 7)))
    full_tree, full = full_records(datacube, tree)
    assert any(np.isnan(v) for points in full.values() for _, _, v in points)
    for leaf in full_tree.leaves:
        assert leaf.result.dtype == np.float64
    banded = banded_records(datacube, tree, select_axes, band_size=3)
    assert_same_records(full, banded)


# ---------------------------------------------------------------------------------------------------------------------
# memory


def tree_bytes(tree):
    total = 0
    for node, _ in iter_nodes(tree):
        total += sys.getsizeof(node) + sys.getsizeof(node.__dict__) + sys.getsizeof(node.values)
        if isinstance(node.values, tuple):
            total += sum(sys.getsizeof(v) for v in node.values)
    return total


def test_tree_memory_per_point_for_1m_point_slice():
    axes = dict(MARS_AXES, param=["167"], step=["0"], number=["1"])
    request = Request(
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
        Box(["latitude", "longitude"], [-90, 0], [90, 360]),
    )
    _, tree, _ = slice_request(mars_options({"type": "regular", "resolution": 360}), axes, request)
    n_points = sum(tree.latitude_point_counts())
    assert n_points > 1_000_000
    per_point = tree_bytes(tree) / n_points
    assert per_point < 16, per_point
