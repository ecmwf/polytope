import sys
import types

import numpy as np
import pytest
from scipy.sparse import csr_array


def _install_fake_mir(monkeypatch, dense_matrix: np.ndarray):
    """Install a fake `mir`/`mir.weight_matrix` module exposing a minimal
    `WeightMatrix` with a `from_feature_regrid` classmethod, mimicking the
    real `mir.WeightMatrix` API closely enough to test `GridInterpolator`
    without the real (heavy, compiled) `mir` dependency.
    """
    full = csr_array(dense_matrix)

    class FakeWeightMatrix:
        def __init__(self, matrix):
            self._m = matrix

        @classmethod
        def from_feature_regrid(cls, in_grid, out_grid, in_indices=(), out_indices=(), kwargs=None, atol=1e-12):
            m = full.copy()
            keep = np.ones(m.shape[0], dtype=bool)
            if len(out_indices):
                keep[:] = False
                keep[list(out_indices)] = True
            m = m.tolil()
            for i in range(m.shape[0]):
                if not keep[i]:
                    m.rows[i] = []
                    m.data[i] = []
            return cls(m.tocsr())

        def to_csr(self):
            return self._m

        @property
        def shape(self):
            return self._m.shape

    mir_module = types.ModuleType("mir")
    weight_matrix_module = types.ModuleType("mir.weight_matrix")
    weight_matrix_module.WeightMatrix = FakeWeightMatrix
    mir_module.weight_matrix = weight_matrix_module
    monkeypatch.setitem(sys.modules, "mir", mir_module)
    monkeypatch.setitem(sys.modules, "mir.weight_matrix", weight_matrix_module)


@pytest.fixture
def dense_matrix():
    # 4 output points x 5 input points, bilinear-ish weights.
    return np.array(
        [
            [0.5, 0.5, 0.0, 0.0, 0.0],
            [0.0, 0.5, 0.5, 0.0, 0.0],
            [0.0, 0.0, 0.0, 1.0, 0.0],
            [0.0, 0.0, 0.0, 0.0, 1.0],
        ]
    )


def test_needed_input_indices(monkeypatch, dense_matrix):
    _install_fake_mir(monkeypatch, dense_matrix)
    from polytope_feature.datacube.interpolation import GridInterpolator

    interp = GridInterpolator(in_grid="H4n", out_grid="O4", method="linear")

    # Only output point 0 and 2 are requested -> need input points {0, 1} and {3}
    needed = interp.needed_input_indices(out_indices=[0, 2])
    np.testing.assert_array_equal(needed, [0, 1, 3])


def test_interpolate(monkeypatch, dense_matrix):
    _install_fake_mir(monkeypatch, dense_matrix)
    from polytope_feature.datacube.interpolation import GridInterpolator

    interp = GridInterpolator(in_grid="H4n", out_grid="O4", method="linear")

    out_indices = [0, 1]
    needed = interp.fetch_plan(out_indices)
    assert needed == [0, 1, 2]

    # pretend GribJump returned these values for the needed input points
    fetched = {0: 10.0, 1: 20.0, 2: 30.0}
    result = interp.interpolate(out_indices, fetched)

    # out[0] = 0.5*10 + 0.5*20 = 15 ; out[1] = 0.5*20 + 0.5*30 = 25
    np.testing.assert_allclose(result, [15.0, 25.0])


def test_mapper_config_to_grid_spec():
    from polytope_feature.datacube.interpolation import mapper_config_to_grid_spec

    class FakeMapperConfig:
        def __init__(self, type_, resolution):
            self.type = type_
            self.resolution = resolution

    assert mapper_config_to_grid_spec(FakeMapperConfig("octahedral", 1280)) == "O1280"
    assert mapper_config_to_grid_spec(FakeMapperConfig("regular", [0.1, 0.1])) == {"grid": [0.1, 0.1]}
    assert mapper_config_to_grid_spec(FakeMapperConfig("healpix", 1024)) == "H1024_nested"


def test_grid_points_octahedral_enumeration_and_bbox():
    from polytope_feature.datacube import grid_points

    mapper = grid_points.build_bare_mapper("octahedral", 4)
    all_lats, all_lons, all_idx = grid_points.enumerate_all_points(mapper)
    assert len(all_lats) == 208
    np.testing.assert_array_equal(all_idx, np.arange(208))

    # Round trip: looking up lat/lon for a subset of indices matches enumeration.
    sub_idx = np.array([0, 5, 207])
    sub_lats, sub_lons = grid_points.latlon_for_indices(mapper, sub_idx)
    np.testing.assert_allclose(sub_lats, all_lats[sub_idx])
    np.testing.assert_allclose(sub_lons, all_lons[sub_idx])

    bbox_lats, bbox_lons, bbox_idx = grid_points.points_in_bbox(mapper, north=90, south=70, east=90, west=0)
    assert len(bbox_idx) > 0
    assert set(bbox_idx.tolist()) <= set(all_idx.tolist())
    assert np.all(bbox_lats >= 70) and np.all(bbox_lats <= 90)
    assert np.all(bbox_lons >= 0) and np.all(bbox_lons <= 90)


def test_group_rows():
    from polytope_feature.datacube import grid_points

    lats = np.array([10.0, 20.0, 10.0, 20.0])
    lons = np.array([5.0, 1.0, 1.0, 3.0])
    idxs = np.array([3, 7, 1, 8])

    unique_lats, lon_rows, flat_idx = grid_points.group_rows(lats, lons, idxs)
    np.testing.assert_array_equal(unique_lats, [10.0, 20.0])
    np.testing.assert_array_equal(lon_rows[0], [1.0, 5.0])
    np.testing.assert_array_equal(lon_rows[1], [1.0, 3.0])
    np.testing.assert_array_equal(flat_idx, [1, 3, 7, 8])


def test_retrieve_interpolated_pipeline_identity_grid(monkeypatch):
    """End-to-end test of the bbox -> needed-input-indices -> bulk fetch ->
    interpolate -> output-grid-leaf pipeline, using an identity weight matrix
    (in_grid == out_grid) so correctness is easy to check: output values at a
    given output index must equal the (synthetic) input value at the same
    index, and the output leaf's lat/lon must match the output grid's.
    """
    from polytope_feature.datacube import grid_points
    from polytope_feature.datacube.interpolated_retrieval import (
        _replace_with_interpolated_leaf,
    )
    from polytope_feature.datacube.interpolation import GridInterpolator
    from polytope_feature.datacube.tensor_index_tree import (
        BulkGridTensorIndexNode,
        TensorIndexTree,
    )

    mapper = grid_points.build_bare_mapper("octahedral", 4)
    n_points = len(mapper.first_axis_vals()) and len(grid_points.enumerate_all_points(mapper)[0])
    identity = np.eye(n_points)
    _install_fake_mir(monkeypatch, identity)

    grid_desc = {"type": "octahedral", "resolution": 4}
    interpolator = GridInterpolator(
        in_grid="O4",
        out_grid="O4",
        in_grid_desc=grid_desc,
        out_grid_desc=grid_desc,
    )

    out_lats, out_lons, out_idx = grid_points.points_in_bbox(mapper, north=90, south=70, east=90, west=0)
    out_unique_lats, out_lon_rows, out_flat_idx = grid_points.group_rows(out_lats, out_lons, out_idx)

    needed_in_idx = interpolator.needed_input_indices(out_flat_idx.tolist())
    # Identity matrix -> needed input indices are exactly the output indices.
    np.testing.assert_array_equal(np.sort(needed_in_idx), np.sort(out_flat_idx))

    in_lats, in_lons = grid_points.latlon_for_indices(mapper, needed_in_idx)
    in_unique_lats, in_lon_rows, in_flat_idx = grid_points.group_rows(in_lats, in_lons, needed_in_idx)

    class FakeAxis:
        def __init__(self, name):
            self.name = name

    lat_ax, lon_ax = FakeAxis("latitude"), FakeAxis("longitude")

    leaf = TensorIndexTree()
    in_node = BulkGridTensorIndexNode([lat_ax, lon_ax], in_unique_lats, in_lon_rows, in_flat_idx)
    leaf.add_child(in_node)

    # Simulate GribJump having returned synthetic values: value == canonical index.
    in_node.result = [in_node.indexes.astype(float)]

    out_node = _replace_with_interpolated_leaf(
        leaf, interpolator, out_unique_lats, out_lon_rows, out_flat_idx, lat_ax, lon_ax
    )

    assert len(leaf.children) == 1
    assert leaf.children[0] is out_node
    np.testing.assert_array_equal(out_node.indexes, out_flat_idx)
    np.testing.assert_allclose(out_node.result[0], out_flat_idx.astype(float))

    all_lats, all_lons, _ = grid_points.enumerate_all_points(mapper)
    np.testing.assert_allclose(out_node.coordinates[:, 0], all_lats[out_node.indexes])
    np.testing.assert_allclose(out_node.coordinates[:, 1], all_lons[out_node.indexes])


def test_extract_grid_bbox_unwraps_single_box_union():
    from polytope_feature.datacube.interpolated_retrieval import _split_grid_shapes
    from polytope_feature.polytope import Request
    from polytope_feature.shapes import Box, Select, Union

    req = Request(
        Select("step", [0]),
        Union(["latitude", "longitude"], Box(["latitude", "longitude"], [10, 20], [30, 40])),
    )
    grid_shapes, remaining = _split_grid_shapes(req, ("latitude", "longitude"))
    assert len(grid_shapes) == 1
    assert [type(s).__name__ for s in remaining] == ["Select"]


def _make_bare_polytope(engine_options):
    """A `Polytope` engine instance without a backing datacube, just enough
    state for `.slice()` to work (used to test slicing against
    `OutputGridDatacube` without needing a real FDB/xarray datacube).
    """
    from polytope_feature.engine.hullslicer import HullSlicer
    from polytope_feature.polytope import Polytope

    p = Polytope.__new__(Polytope)
    p.compressed_axes = []
    p.context = {}
    p.engine_options = engine_options
    p.engines = {"hullslicer": HullSlicer()}
    p.ax_is_unsliceable = {}
    return p


def _octahedral_axis_options(resolution=4):
    from polytope_feature.options import AxisConfig

    return [
        AxisConfig(
            axis_name="values",
            transformations=[
                {"name": "mapper", "type": "octahedral", "resolution": resolution, "axes": ["latitude", "longitude"]}
            ],
        ),
        AxisConfig(axis_name="latitude", transformations=[{"name": "reverse", "is_reverse": True}]),
        AxisConfig(axis_name="longitude", transformations=[{"name": "cyclic", "range": [0, 360]}]),
    ]


class _FakeDatacube:
    def __init__(self, axis_options):
        self.axis_options = axis_options


def test_output_grid_datacube_slices_box_shape():
    from polytope_feature.datacube.interpolated_retrieval import _collect_latlon_pairs
    from polytope_feature.datacube.output_grid_datacube import (
        OutputGridDatacube,
        build_output_grid_axis_options,
    )
    from polytope_feature.shapes import Box

    datacube = _FakeDatacube(_octahedral_axis_options(4))
    out_grid_desc = {"type": "octahedral", "resolution": 4}
    axis_options, grid_axes = build_output_grid_axis_options(datacube, out_grid_desc)
    assert grid_axes == ("latitude", "longitude")

    output_dc = OutputGridDatacube(axis_options)
    p = _make_bare_polytope({"latitude": "hullslicer", "longitude": "hullslicer"})

    box = Box(["latitude", "longitude"], [70, 0], [90, 90])
    tree = p.slice(output_dc, box.polytope())

    pairs = _collect_latlon_pairs(tree)
    assert len(pairs) > 0
    for lat, lon in pairs:
        assert 70 <= lat <= 90
        assert 0 <= lon <= 90


def test_output_grid_datacube_slices_disk_shape():
    """Proves interpolation works with non-bounding-box shapes too (eg. Disk,
    Polygon, Path, ...) since it reuses Polytope's normal slicing mechanism.
    """
    from polytope_feature.datacube.interpolated_retrieval import _collect_latlon_pairs
    from polytope_feature.datacube.output_grid_datacube import (
        OutputGridDatacube,
        build_output_grid_axis_options,
    )
    from polytope_feature.shapes import Box, Disk

    datacube = _FakeDatacube(_octahedral_axis_options(4))
    out_grid_desc = {"type": "octahedral", "resolution": 4}
    axis_options, _ = build_output_grid_axis_options(datacube, out_grid_desc)

    box_dc = OutputGridDatacube(axis_options)
    disk_dc = OutputGridDatacube(axis_options)
    p = _make_bare_polytope({"latitude": "hullslicer", "longitude": "hullslicer"})

    box = Box(["latitude", "longitude"], [-90, 0], [90, 360])
    box_tree = p.slice(box_dc, box.polytope())
    box_pairs = set(_collect_latlon_pairs(box_tree))

    disk = Disk(["latitude", "longitude"], centre=[80, 45], radius=[15, 15])
    disk_tree = p.slice(disk_dc, disk.polytope())
    disk_pairs = set(_collect_latlon_pairs(disk_tree))

    assert len(disk_pairs) > 0
    # The disk only selects points near its centre, so it must be a strict subset of
    # every grid point (shown here via the full-globe Box), and much smaller than it.
    assert disk_pairs <= box_pairs
    assert len(disk_pairs) < len(box_pairs)


def test_slice_grid_shapes_end_to_end():
    """Full `_slice_grid_shapes` helper (as used by `retrieve_interpolated`),
    using a real hullslicer engine and a real `OutputGridDatacube`.
    """
    from polytope_feature.datacube.interpolated_retrieval import _slice_grid_shapes
    from polytope_feature.shapes import Box

    datacube = _FakeDatacube(_octahedral_axis_options(4))
    out_grid_desc = {"type": "octahedral", "resolution": 4}
    p = _make_bare_polytope({"latitude": "hullslicer", "longitude": "hullslicer"})

    box = Box(["latitude", "longitude"], [70, 0], [90, 90])
    unique_lats, lon_rows, flat_idx = _slice_grid_shapes(p, [box], out_grid_desc, datacube)

    assert len(flat_idx) > 0
    assert len(unique_lats) == len(lon_rows)
    assert len(flat_idx) == sum(len(row) for row in lon_rows)


class _FakeInputDatacube:
    """A minimal, real `Datacube` subclass standing in for `FDBDatacube` in
    full `retrieve_interpolated()` tests: a "step" axis plus the standard
    octahedral lat/lon mapper, with a `.get()` that fills bulk grid leaves
    with synthetic data (value == canonical grid index), so the whole
    "slice everything else -> attach input bulk leaf -> fetch -> interpolate
    -> replace with output bulk leaf" pipeline can be exercised without FDB.
    """


def _make_fake_input_datacube(resolution=4, steps=(0, 1)):
    from polytope_feature.datacube.backends.datacube import Datacube
    from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode

    axis_options = _octahedral_axis_options(resolution)

    class FakeInputDatacube(Datacube):
        def __init__(self):
            super().__init__(axis_options=axis_options, compressed_axes_options=["latitude", "longitude"])
            self._axes = {}
            self.treated_axes = []
            self.complete_axes = []
            self.grid_transformation = None
            self.coordinates = {"step": list(steps), "values": []}

            for name, values in self.coordinates.items():
                opt = next((o for o in axis_options if o.axis_name == name), None)
                self._check_and_add_axes(opt, name, values)
                self.treated_axes.append(name)
                self.complete_axes.append(name)
            for name in list(self._axes.keys()):
                if name not in self.treated_axes:
                    opt = next((o for o in axis_options if o.axis_name == name), None)
                    val = self._axes[name].type
                    self._check_and_add_axes(opt, name, val)

        def select(self, path, unmapped_path):
            return self.coordinates

        def datacube_natural_indexes(self, axis, subarray):
            return subarray.get(axis.name, None)

        def find_point_cloud(self):
            return None

        def get(self, requests, context=None):
            def walk(node):
                for child in list(node.children):
                    if isinstance(child, BulkGridTensorIndexNode):
                        # Synthetic "GribJump" response: value == canonical grid index.
                        child.result.append(child.indexes.astype(float))
                    else:
                        walk(child)

            walk(requests)

    return FakeInputDatacube()


def test_retrieve_interpolated_end_to_end(monkeypatch):
    """Full `retrieve_interpolated()` run (slice output grid with a real Box shape,
    slice remaining axes, fetch via a fake datacube, interpolate, replace leaves),
    using an identity weight matrix so correctness is easy to check.
    """
    from polytope_feature.datacube import grid_points
    from polytope_feature.datacube.interpolated_retrieval import retrieve_interpolated
    from polytope_feature.datacube.interpolation import GridInterpolator
    from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
    from polytope_feature.engine.hullslicer import HullSlicer
    from polytope_feature.polytope import Polytope, Request
    from polytope_feature.shapes import Box, Select

    mapper = grid_points.build_bare_mapper("octahedral", 4)
    n_points = len(grid_points.enumerate_all_points(mapper)[0])
    identity = np.eye(n_points)
    _install_fake_mir(monkeypatch, identity)

    grid_desc = {"type": "octahedral", "resolution": 4}
    interpolator = GridInterpolator(in_grid="O4", out_grid="O4", in_grid_desc=grid_desc, out_grid_desc=grid_desc)

    datacube = _make_fake_input_datacube(resolution=4, steps=(0, 1))
    datacube.interpolator = interpolator

    p = Polytope.__new__(Polytope)
    p.datacube = datacube
    p.compressed_axes = []
    p.context = {}
    p.engine_options = {"step": "hullslicer", "latitude": "hullslicer", "longitude": "hullslicer"}
    p.engines = {"hullslicer": HullSlicer()}
    p.ax_is_unsliceable = {}

    request = Request(
        Select("step", [0, 1]),
        Box(["latitude", "longitude"], [70, 0], [90, 90]),
    )
    tree = retrieve_interpolated(p, request)

    leaves = tree.leaves
    # One leaf per "step" value (not compressed in this fake datacube).
    assert len(leaves) == 2
    for leaf in leaves:
        assert isinstance(leaf, BulkGridTensorIndexNode)
        out_node = leaf
        # Identity weight matrix -> interpolated value == canonical index (same as the
        # fake "GribJump" response).
        assert len(out_node.result) == 1
        np.testing.assert_allclose(out_node.result[0], out_node.indexes.astype(float))
        # Only output-grid points, all within the requested box.
        assert np.all(out_node.coordinates[:, 0] >= 70) and np.all(out_node.coordinates[:, 0] <= 90)
        assert np.all(out_node.coordinates[:, 1] >= 0) and np.all(out_node.coordinates[:, 1] <= 90)
