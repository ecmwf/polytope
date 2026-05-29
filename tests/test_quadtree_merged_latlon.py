"""
Unit tests for the merged latlon quadtree feature.
No pyfdb / eccodes required — pure unit tests.
"""

import types
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mapper_options(
    grid_type="octahedral",
    resolution=32,
    axes=None,
    md5_hash=None,
    local=None,
    axis_reversed=None,
):
    """Build a minimal mapper_options namespace accepted by DatacubeMapper."""
    if axes is None:
        axes = ["latitude", "longitude"]
    opts = types.SimpleNamespace(
        type=grid_type,
        resolution=resolution,
        axes=axes,
        md5_hash=md5_hash,
        local=local,
        axis_reversed=axis_reversed,
    )
    return opts


# ---------------------------------------------------------------------------
# (a) DatacubeMapper initialises with merged_latlon=False
#     and compressed_grid_axes returns [] when merged_latlon=True
# ---------------------------------------------------------------------------


class TestDatacubeMapperMergedLatlon:
    def _make_mapper(self):
        from polytope_feature.datacube.transformations.datacube_mappers.datacube_mappers import (
            DatacubeMapper,
        )

        opts = _make_mapper_options()
        return DatacubeMapper("values", opts)

    def test_merged_latlon_defaults_false(self):
        mapper = self._make_mapper()
        assert mapper.merged_latlon is False

    def test_compressed_grid_axes_normal(self):
        """When merged_latlon is False, compressed_grid_axes is non-empty."""
        mapper = self._make_mapper()
        axes = mapper.compressed_grid_axes
        assert isinstance(axes, list)
        assert len(axes) > 0

    def test_compressed_grid_axes_empty_when_merged(self):
        """When merged_latlon is True, compressed_grid_axes must return []."""
        mapper = self._make_mapper()
        mapper.merged_latlon = True
        assert mapper.compressed_grid_axes == []

    def test_merged_latlon_toggle_restores_axes(self):
        """Toggling merged_latlon back to False restores the original axes."""
        mapper = self._make_mapper()
        original = mapper.compressed_grid_axes[:]
        mapper.merged_latlon = True
        assert mapper.compressed_grid_axes == []
        mapper.merged_latlon = False
        assert mapper.compressed_grid_axes == original


# ---------------------------------------------------------------------------
# (b) IrregularGridMapper.unmap((lat, lon), None, [idx]) returns idx
# ---------------------------------------------------------------------------


class TestIrregularGridMapperUnmap:
    def _make_irregular_mapper(self):
        from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.irregular import (
            IrregularGridMapper,
        )

        mapped_axes = ["latitude", "longitude"]
        base_axis = "values"

        # We need a mapper_options that won't trigger actual grid file loading.
        # Patch generate_final_irregular_transformation so no real data needed.
        with patch.object(
            IrregularGridMapper,
            "generate_final_irregular_transformation",
            return_value=MagicMock(),
        ):
            opts = _make_mapper_options(grid_type="icon", axes=mapped_axes)
            mapper = IrregularGridMapper(base_axis, mapped_axes, 1, mapper_options=opts)
        return mapper

    def test_unmap_returns_single_idx(self):
        mapper = self._make_irregular_mapper()
        result = mapper.unmap((10.0, 20.0), None, [42])
        assert result == 42

    def test_unmap_returns_first_element(self):
        mapper = self._make_irregular_mapper()
        result = mapper.unmap((0.0, 0.0), None, [7])
        assert result == 7

    def test_unmap_with_various_indices(self):
        mapper = self._make_irregular_mapper()
        for idx in [0, 1, 100, 999]:
            assert mapper.unmap((1.0, 2.0), None, [idx]) == idx


# ---------------------------------------------------------------------------
# (c) change_val_type returns [(0.0, 0.0)] when merged_latlon=True
# ---------------------------------------------------------------------------


class TestChangeValType:
    def _make_mapper(self):
        from polytope_feature.datacube.transformations.datacube_mappers.datacube_mappers import (
            DatacubeMapper,
        )

        opts = _make_mapper_options()
        return DatacubeMapper("values", opts)

    def test_change_val_type_merged_false_returns_float(self):
        mapper = self._make_mapper()
        mapper.merged_latlon = False
        result = mapper.change_val_type("latitude", [0.0])
        assert result == [0.0]

    def test_change_val_type_merged_true_returns_tuple_list(self):
        mapper = self._make_mapper()
        mapper.merged_latlon = True
        result = mapper.change_val_type("latitude", [(0.0, 0.0)])
        assert result == [(0.0, 0.0)]

    def test_change_val_type_merged_true_any_axis_name(self):
        """axis_name is ignored; only merged_latlon matters."""
        mapper = self._make_mapper()
        mapper.merged_latlon = True
        for axis in ["latitude", "longitude", "values"]:
            assert mapper.change_val_type(axis, []) == [(0.0, 0.0)]


# ---------------------------------------------------------------------------
# (d) QuadTreeSlicer._build_branch sets merged_latlon=True and
#     _build_sliceable_child creates ONE merged node per point
# ---------------------------------------------------------------------------


class TestQuadTreeSlicerMergedNodes:
    def test_build_branch_sets_merged_latlon(self):
        """_build_branch must set datacube.grid_transformation.merged_latlon=True."""
        from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer

        slicer = QuadTreeSlicer.__new__(QuadTreeSlicer)

        # Minimal mock: node has no unsliced_polytopes so inner loop is skipped
        node = {"unsliced_polytopes": []}

        datacube = MagicMock()
        datacube.grid_transformation = MagicMock()
        datacube.grid_transformation.merged_latlon = False

        ax = MagicMock()
        ax.name = "latitude"

        slicer._build_branch(ax, node, datacube, [], None)

        assert datacube.grid_transformation.merged_latlon is True

    def test_build_sliceable_child_creates_one_merged_node_per_point(self):
        """
        For each extracted point, exactly ONE child is created on the lat axis
        carrying a (lat, lon) tuple — not two nested nodes.
        """
        from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer, use_rust

        points = [(10.0, 20.0), (30.0, 40.0)]

        slicer = QuadTreeSlicer.__new__(QuadTreeSlicer)
        slicer.points = points

        # Stub extract_single to return indices of both points
        slicer.extract_single = MagicMock(
            return_value=(
                [0, 1]
                if use_rust
                else [
                    MagicMock(item=(points[0][0], points[0][1]), index=0),
                    MagicMock(item=(points[1][0], points[1][1]), index=1),
                ]
            )
        )

        created_children = []

        def fake_create_child(ax, values, indexes):
            child = MagicMock()
            # child["unsliced_polytopes"] must return a list containing polytope
            # so that the subsequent .remove(polytope) works
            child.__getitem__ = MagicMock(return_value=[polytope])
            child.__setitem__ = MagicMock()
            child.indexes = []
            created_children.append((ax, values))
            return child, None

        node = MagicMock()
        node.__getitem__ = MagicMock(return_value=[])
        node.__setitem__ = MagicMock()
        node.__delitem__ = MagicMock()
        node.create_child = MagicMock(side_effect=fake_create_child)

        polytope = MagicMock()
        polytope._axes = ["latitude"]

        lat_ax = MagicMock()
        lat_ax.name = "latitude"

        datacube = MagicMock()
        next_nodes = []

        slicer._build_sliceable_child(polytope, lat_ax, node, datacube, next_nodes, None)

        # Should have created exactly 2 children (one per point)
        assert len(created_children) == 2

        # Each child value must be a (lat, lon) tuple wrapped in an outer tuple
        for ax, values in created_children:
            # values is passed as ((lat_val, lon_val),)
            assert isinstance(values, tuple)
            assert len(values) == 1
            inner = values[0]
            assert isinstance(inner, tuple)
            assert len(inner) == 2  # (lat, lon) — not a nested tree structure
