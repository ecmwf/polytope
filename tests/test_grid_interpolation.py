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


def _brute_force_all_points(mapper):
    """Ground truth: enumerate every point the slow way, via second_axis_vals()/unmap()."""
    lats_out, lons_out, idxs_out = [], [], []
    for lat in mapper.first_axis_vals():
        lons = mapper.second_axis_vals([lat])
        idxs = mapper.unmap([lat], lons)
        lats_out.extend([lat] * len(lons))
        lons_out.extend(lons)
        idxs_out.extend(idxs)
    order = np.argsort(idxs_out)
    return np.asarray(lats_out)[order], np.asarray(lons_out)[order], np.asarray(idxs_out)[order]


@pytest.mark.parametrize(
    "grid_desc",
    [
        {"type": "octahedral", "resolution": 4},
        {"type": "regular", "resolution": 4},
        {"type": "healpix", "resolution": 4},
    ],
)
def test_ring_index_matches_brute_force(grid_desc):
    """`RingIndex`'s O(log num_rings) lookup must match the brute-force (O(num_points))
    enumeration exactly, for every ring-based structured grid type.
    """
    from polytope_feature.datacube import grid_points

    mapper = grid_points.grid_spec_to_mapper(grid_desc)
    all_lats, all_lons, all_idx = _brute_force_all_points(mapper)
    assert np.array_equal(all_idx, np.arange(len(all_idx)))

    ri = grid_points.RingIndex(mapper)
    assert ri.total_points == len(all_idx)

    idx = np.random.default_rng(0).choice(len(all_idx), size=min(30, len(all_idx)), replace=False)
    lats, lons = ri.latlon_for_indices(idx)
    np.testing.assert_allclose(lats, all_lats[idx])
    np.testing.assert_allclose(lons, all_lons[idx], atol=1e-8)


def test_unstructured_grid_latlon_for_indices():
    from polytope_feature.datacube import grid_points

    points = [(10.0, 20.0), (30.0, 40.0), (50.0, 60.0)]
    mapper = grid_points.grid_spec_to_mapper({"type": "unstructured", "points": points})
    assert mapper.is_irregular
    assert mapper.point_count() == 3

    ri = grid_points.RingIndex(mapper)
    lats, lons = ri.latlon_for_indices([0, 2])
    np.testing.assert_allclose(lats, [10.0, 50.0])
    np.testing.assert_allclose(lons, [20.0, 60.0])


def test_nested_healpix_remap_round_trip():
    """The nested->ring index remap must round-trip exactly through the
    already-tested forward `ring_to_nested()`, and give lat/lon consistent
    with the regular (ring-ordered) HEALPix grid.
    """
    from polytope_feature.datacube import grid_points

    nested = grid_points.grid_spec_to_mapper({"type": "healpix_nested", "resolution": 8})
    ring_major = np.arange(nested.point_count())
    nest_idx = nested.ring_to_nested(ring_major)

    back = nested.remap_canonical_index(nest_idx)
    np.testing.assert_array_equal(back, ring_major)

    # lat/lon for a nested index must match the equivalent ring-major point on the
    # plain (ring-ordered) HEALPix grid of the same resolution.
    ring_mapper = grid_points.grid_spec_to_mapper({"type": "healpix", "resolution": 8})
    ri_ring = grid_points.RingIndex(ring_mapper)
    ri_nested = grid_points.RingIndex(nested)

    sample_ring_major = np.array([0, 5, 100, 300, nested.point_count() - 1])
    sample_nest = nested.ring_to_nested(sample_ring_major)

    lats_ring, lons_ring = ri_ring.latlon_for_indices(sample_ring_major)
    lats_nested, lons_nested = ri_nested.latlon_for_indices(sample_nest)
    np.testing.assert_allclose(lats_nested, lats_ring)
    np.testing.assert_allclose(lons_nested, lons_ring)


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


def _make_fake_input_datacube(resolution=4, steps=(0, 1), levels=None):
    """A minimal, real `Datacube` subclass standing in for `FDBDatacube`: a "step"
    (and optionally "levelist") axis plus the standard octahedral lat/lon mapper,
    with a `.get()` that fills bulk grid leaves with synthetic data (value ==
    canonical grid index), so the whole interpolated-retrieve pipeline can be
    exercised without FDB.
    """
    from polytope_feature.datacube.backends.datacube import Datacube
    from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode

    axis_options = _octahedral_axis_options(resolution)
    coordinates = {"step": list(steps)}
    if levels is not None:
        coordinates["levelist"] = list(levels)
    coordinates["values"] = []

    class FakeInputDatacube(Datacube):
        def __init__(self):
            super().__init__(axis_options=axis_options, compressed_axes_options=["latitude", "longitude"])
            self._axes = {}
            self.treated_axes = []
            self.complete_axes = []
            self.grid_transformation = None
            self.coordinates = coordinates

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


def _make_interpolated_polytope(datacube, interpolator, engine_options=None):
    from polytope_feature.engine.hullslicer import HullSlicer
    from polytope_feature.polytope import Polytope

    datacube.interpolator = interpolator
    p = Polytope.__new__(Polytope)
    p.datacube = datacube
    p.compressed_axes = []
    p.context = {}
    p.engine_options = engine_options or {
        "step": "hullslicer",
        "levelist": "hullslicer",
        "latitude": "hullslicer",
        "longitude": "hullslicer",
    }
    p.engines = {"hullslicer": HullSlicer()}
    p.ax_is_unsliceable = {}
    return p


def _identity_interpolator(monkeypatch, resolution=4):
    from polytope_feature.datacube import grid_points
    from polytope_feature.datacube.interpolation import GridInterpolator

    mapper = grid_points.grid_spec_to_mapper({"type": "octahedral", "resolution": resolution})
    n_points = grid_points.RingIndex(mapper).total_points
    _install_fake_mir(monkeypatch, np.eye(n_points))

    grid_desc = {"type": "octahedral", "resolution": resolution}
    return GridInterpolator(in_grid="O4", out_grid="O4", in_grid_desc=grid_desc, out_grid_desc=grid_desc)


class TestRetrieveWithInterpolation:
    """`Polytope.retrieve()` itself, with `datacube.interpolator` set - these exercise
    the real, unified retrieve path (mapper swap + single slice()/get() call), not a
    separate reimplementation, for various shapes and dimensionalities.
    """

    def test_box_2d(self, monkeypatch):
        from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
        from polytope_feature.polytope import Request
        from polytope_feature.shapes import Box, Select

        interpolator = _identity_interpolator(monkeypatch)
        datacube = _make_fake_input_datacube(resolution=4, steps=(0, 1))
        p = _make_interpolated_polytope(datacube, interpolator)

        request = Request(Select("step", [0, 1]), Box(["latitude", "longitude"], [70, 0], [90, 90]))
        tree = p.retrieve(request)

        leaves = tree.leaves
        assert len(leaves) == 2  # one per "step" value (not compressed)
        for leaf in leaves:
            assert isinstance(leaf, BulkGridTensorIndexNode)
            assert len(leaf.result) == 1
            np.testing.assert_allclose(leaf.result[0], leaf.indexes.astype(float))
            assert np.all(leaf.coordinates[:, 0] >= 70) and np.all(leaf.coordinates[:, 0] <= 90)
            assert np.all(leaf.coordinates[:, 1] >= 0) and np.all(leaf.coordinates[:, 1] <= 90)

    def test_disk_2d(self, monkeypatch):
        from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
        from polytope_feature.polytope import Request
        from polytope_feature.shapes import Disk, Select

        interpolator = _identity_interpolator(monkeypatch)
        datacube = _make_fake_input_datacube(resolution=4, steps=(0,))
        p = _make_interpolated_polytope(datacube, interpolator)

        request = Request(Select("step", [0]), Disk(["latitude", "longitude"], centre=[80, 45], radius=[15, 15]))
        tree = p.retrieve(request)

        leaves = tree.leaves
        assert len(leaves) == 1
        leaf = leaves[0]
        assert isinstance(leaf, BulkGridTensorIndexNode)
        assert leaf.point_count > 0
        np.testing.assert_allclose(leaf.result[0], leaf.indexes.astype(float))

    def test_higher_dimensional_box_lat_lon_plus_levelist(self, monkeypatch):
        """A single Box shape spanning latitude, longitude *and* levelist jointly -
        the exact "higher-dimensional shape" case the mapper-swap/single-slice
        design handles with no special-casing at all.
        """
        from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
        from polytope_feature.polytope import Request
        from polytope_feature.shapes import Box, Select

        interpolator = _identity_interpolator(monkeypatch)
        datacube = _make_fake_input_datacube(resolution=4, steps=(0,), levels=(1, 2, 3))
        p = _make_interpolated_polytope(datacube, interpolator)

        request = Request(
            Select("step", [0]),
            Box(["latitude", "longitude", "levelist"], [70, 0, 1], [90, 90, 2]),
        )
        tree = p.retrieve(request)

        leaves = tree.leaves
        # One leaf per (step, levelist) combination selected: step=0 (only one), levelist in {1,2}
        assert len(leaves) == 2
        for leaf in leaves:
            assert isinstance(leaf, BulkGridTensorIndexNode)
            np.testing.assert_allclose(leaf.result[0], leaf.indexes.astype(float))
            assert np.all(leaf.coordinates[:, 0] >= 70) and np.all(leaf.coordinates[:, 0] <= 90)
            assert np.all(leaf.coordinates[:, 1] >= 0) and np.all(leaf.coordinates[:, 1] <= 90)

    def test_single_nearest_point(self, monkeypatch):
        """A single `Point(method="nearest")` query (eg. polytope-mars's Position
        feature) must resolve to exactly one output grid point and interpolate it
        from the input grid correctly.
        """
        from polytope_feature.datacube import grid_points
        from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
        from polytope_feature.polytope import Request
        from polytope_feature.shapes import Point, Select

        interpolator = _identity_interpolator(monkeypatch)
        datacube = _make_fake_input_datacube(resolution=4, steps=(0,))
        p = _make_interpolated_polytope(datacube, interpolator)

        mapper = grid_points.grid_spec_to_mapper({"type": "octahedral", "resolution": 4})
        target_lat = mapper.first_axis_vals()[2]
        target_lon = mapper.second_axis_vals([target_lat])[3]

        request = Request(
            Select("step", [0]),
            Point(["latitude", "longitude"], [[target_lat + 0.01, target_lon + 0.01]], method="nearest"),
        )
        tree = p.retrieve(request)

        leaves = tree.leaves
        assert len(leaves) == 1
        leaf = leaves[0]
        assert isinstance(leaf, BulkGridTensorIndexNode)
        assert leaf.point_count == 1
        np.testing.assert_allclose(leaf.coordinates[0], [target_lat, target_lon])
        # Identity weight matrix -> interpolated value == canonical index of that nearest point.
        expected_idx = mapper.unmap([target_lat], [target_lon])[0]
        np.testing.assert_allclose(leaf.result[0], [float(expected_idx)])
        assert leaf.indexes[0] == expected_idx

    def test_interpolation_does_not_leak_into_normal_requests(self, monkeypatch):
        """After an interpolated retrieve, the datacube's grid mapper must be back to
        the real input grid - a subsequent normal (non-interpolated) retrieve must
        behave exactly as if interpolation had never been used.
        """
        from polytope_feature.polytope import Request
        from polytope_feature.shapes import Box, Select

        interpolator = _identity_interpolator(monkeypatch)
        datacube = _make_fake_input_datacube(resolution=4, steps=(0,))
        original_mapper = datacube.grid_transformation
        p = _make_interpolated_polytope(datacube, interpolator)

        p.retrieve(Request(Select("step", [0]), Box(["latitude", "longitude"], [70, 0], [90, 90])))
        assert datacube.grid_transformation is original_mapper
        for axis_name in ("latitude", "longitude"):
            assert original_mapper in datacube._axes[axis_name].transformations

        datacube.interpolator = None
        tree = p.slice(
            datacube, Request(Select("step", [0]), Box(["latitude", "longitude"], [70, 0], [90, 90])).polytopes()
        )
        assert len(tree.leaves) > 0
