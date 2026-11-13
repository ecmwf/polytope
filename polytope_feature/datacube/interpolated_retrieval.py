"""Grid-interpolated retrieval, integrated directly into `Polytope.retrieve()`.

When `self.datacube.interpolator` is set (ie. the "interpolation" Polytope
option was used), `retrieve()` temporarily swaps the "mapper" transformation
on the datacube's lat/lon axes for one describing the *output* grid, and
runs the exact same `self.slice()` call it always does. Because the mapper
transformation is the only thing that knows how to turn lat/lon shapes into
grid-point candidates/indices, this one swap is enough to make the *normal*
slicing mechanism - whatever shape (Box, Disk, Polygon, Path, Union, ...),
whatever other axes it also spans (level, step, ...), whatever engine
(hullslicer/quadtree/point-in-polygon) - resolve against the output grid
instead of the input grid, with no special-casing of shapes or dimensions
needed at all.

Once sliced, the lat/lon axes are restored to the real (input) grid, and the
resulting tree is walked to:

1. Work out, for every distinct combination of the other axes, which output
   grid points were selected (`_collect_latlon_pairs`).
2. Use `GridInterpolator.needed_input_indices()` to work out exactly which
   *input* grid points are needed to interpolate those - typically a small
   fraction of the full input grid.
3. Replace that part of the tree with a single `BulkGridTensorIndexNode`
   (the same mechanism `bulk_grid_leaves` uses) addressing exactly those
   input points - so `datacube.get()` fetches them in one batched request,
   never as individual nearest-neighbour point queries.
4. After `.get()`, multiply the fetched values through the interpolation
   weight matrix and replace the input-grid bulk leaf with an output-grid
   one - so the final tree only ever exposes output-grid points.

Grid point ordering assumption: the canonical point index produced by a
grid mapper's `unmap()` (used by Polytope/GribJump to address a field) is
assumed to match the native point ordering mir's weight matrix is built
against for the same grid type/resolution.
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from . import grid_points
from .tensor_index_tree import (
    BulkGridTensorIndexNode,
    BulkMergedTensorIndexNode,
    MergedTensorIndexNode,
)
from .transformations.datacube_mappers.datacube_mappers import DatacubeMapper


class _GridMapperSwap:
    """Context manager that temporarily replaces the `DatacubeMapper`
    transformation on a datacube's grid (lat/lon) axes with one for a
    different grid, then restores the original on exit.
    """

    def __init__(self, datacube, grid_axes, new_mapper_config):
        self.datacube = datacube
        self.grid_axes = grid_axes
        self.new_mapper_config = new_mapper_config
        self._originals = {}
        self._old_grid_transformation = None

    def __enter__(self):
        old_axis_name = self.datacube.grid_transformation.old_axis
        new_mapper = DatacubeMapper(name=old_axis_name, mapper_options=self.new_mapper_config)
        self._old_grid_transformation = self.datacube.grid_transformation
        for axis_name in self.grid_axes:
            axis = self.datacube._axes[axis_name]
            for i, transform in enumerate(axis.transformations):
                if isinstance(transform, DatacubeMapper):
                    self._originals[axis_name] = (i, transform)
                    axis.transformations[i] = new_mapper
                    break
        self.datacube.grid_transformation = new_mapper
        return new_mapper

    def __exit__(self, *exc):
        for axis_name, (i, old_transform) in self._originals.items():
            self.datacube._axes[axis_name].transformations[i] = old_transform
        self.datacube.grid_transformation = self._old_grid_transformation
        return False


def _build_output_mapper_config(datacube, out_grid_desc):
    """A `MapperConfig` for the output grid, mirroring the input grid's own
    mapper config (same "axes", local area, axis orientation, ...) but with
    the type/resolution/uuid/points swapped for the output grid's.
    """
    input_config = datacube.grid_transformation.mapper_options
    update = {
        "type": out_grid_desc["type"],
        "resolution": out_grid_desc.get("resolution"),
        "uuid": out_grid_desc.get("uuid"),
        "points": out_grid_desc.get("points"),
        "md5_hash": None,
    }
    return input_config.model_copy(deep=True, update=update)


def _is_grid_leaf_parent(node, lat_axis_name):
    """True if `node`'s children are the lat/lon subtree for one combination
    of the other axes (ie. `node` is the node to attach/replace grid data
    under), for either the nested (hullslicer) or merged/bulk-merged (eg.
    quadtree/point-in-polygon, or `bulk_grid_leaves`) tree representations.
    """
    children = list(node.children)
    if not children:
        return False
    first = children[0]
    if isinstance(first, MergedTensorIndexNode):
        return lat_axis_name in {axis.name for axis in first.axes}
    return getattr(first, "axis", None) is not None and first.axis.name == lat_axis_name


def _find_grid_parent_nodes(tree, lat_axis_name) -> List:
    results = []

    def walk(node):
        if _is_grid_leaf_parent(node, lat_axis_name):
            results.append(node)
            return
        for child in node.children:
            walk(child)

    walk(tree)
    return results


def _collect_latlon_pairs(node) -> List[Tuple[float, float]]:
    """All (lat, lon) pairs selected under a grid-parent node (see
    `_find_grid_parent_nodes`), regardless of which tree representation was
    used to select them.
    """
    first_child = node.children[0]
    if isinstance(first_child, MergedTensorIndexNode):
        pairs = []
        for child in node.children:
            if isinstance(child, BulkMergedTensorIndexNode):
                pairs.extend(tuple(row) for row in child.coordinates.tolist())
            else:
                pairs.append(tuple(child.values))
        return pairs

    pairs = []
    for lat_node in node.children:
        for lon_node in lat_node.children:
            for lat in lat_node.values:
                for lon in lon_node.values:
                    pairs.append((lat, lon))
    return pairs


def _pairs_to_rows(mapper, pairs: List[Tuple[float, float]]):
    """Convert (lat, lon) pairs selected on a grid into latitude-major rows
    with their canonical grid indices (via the mapper's own `unmap()`,
    batched one call per distinct latitude).
    """
    from collections import defaultdict

    by_lat = defaultdict(list)
    for lat, lon in pairs:
        by_lat[lat].append(lon)

    lats_out, lons_out, idx_out = [], [], []
    for lat, lons in by_lat.items():
        idxs = mapper.unmap([lat], lons)
        lats_out.extend([lat] * len(lons))
        lons_out.extend(lons)
        idx_out.extend(idxs)

    return grid_points.group_rows(np.asarray(lats_out), np.asarray(lons_out), np.asarray(idx_out))


def slice_with_interpolation(polytope_engine, datacube, polytopes):
    """Slice `polytopes` against the datacube with its lat/lon axes
    temporarily remapped onto the output grid, then prepare the tree's
    grid subtrees to be fetched from the *input* grid instead. Returns
    (request_tree, attachments), where `attachments` is the bookkeeping
    `finish_interpolation()` needs after `datacube.get()`.
    """
    interpolator = datacube.interpolator
    grid_axes = tuple(datacube.grid_transformation.mapper_options.axes)
    out_mapper_config = _build_output_mapper_config(datacube, interpolator.out_grid_desc)

    with _GridMapperSwap(datacube, grid_axes, out_mapper_config) as out_mapper:
        request_tree = polytope_engine.slice(datacube, polytopes)

        grid_parents = _find_grid_parent_nodes(request_tree, grid_axes[0])

        # Resolve "nearest"/"surrounding" candidate windows down to the actual nearest
        # output grid point(s), same as the normal (non-interpolated) path does.
        if len(datacube.nearest_search) > 0 and hasattr(datacube, "nearest_lat_lon_search"):
            for node in grid_parents:
                datacube.nearest_lat_lon_search(node)

        in_mapper = grid_points.grid_spec_to_mapper(interpolator.in_grid_desc)
        lat_ax = datacube._axes[grid_axes[0]]
        lon_ax = datacube._axes[grid_axes[1]]

        attachments = []
        for node in grid_parents:
            pairs = _collect_latlon_pairs(node)
            if len(pairs) == 0:
                node.remove_branch()
                continue

            out_unique_lats, out_lon_rows, out_flat_idx = _pairs_to_rows(out_mapper, pairs)
            needed_in_idx = interpolator.needed_input_indices(out_flat_idx.tolist())
            in_lats, in_lons = grid_points.latlon_for_indices(in_mapper, needed_in_idx)
            in_unique_lats, in_lon_rows, in_flat_idx = grid_points.group_rows(in_lats, in_lons, needed_in_idx)

            for child in list(node.children):
                node.children.remove(child)
                child._parent = None
            in_node = BulkGridTensorIndexNode([lat_ax, lon_ax], in_unique_lats, in_lon_rows, in_flat_idx)
            node.add_child(in_node)

            attachments.append((node, out_unique_lats, out_lon_rows, out_flat_idx))

    if len(attachments) == 0:
        raise ValueError("Interpolation is enabled but the request selects no output grid points")

    return request_tree, attachments


def finish_interpolation(datacube, attachments, interpolator):
    """After `datacube.get()` has populated the input-grid bulk leaves
    `slice_with_interpolation()` attached, interpolate their values and
    replace them with the corresponding output-grid bulk leaves.
    """
    grid_axes = tuple(datacube.grid_transformation.mapper_options.axes)
    lat_ax = datacube._axes[grid_axes[0]]
    lon_ax = datacube._axes[grid_axes[1]]

    for node, out_unique_lats, out_lon_rows, out_flat_idx in attachments:
        in_node = node.children[0]
        assert isinstance(in_node, BulkGridTensorIndexNode)

        out_results = []
        for combo_values in in_node.result:
            if combo_values is None or len(combo_values) == 0:
                out_results.append(np.full(len(out_flat_idx), None, dtype=object))
                continue
            input_values = dict(zip(in_node.indexes.tolist(), np.asarray(combo_values).tolist()))
            out_results.append(interpolator.interpolate(out_flat_idx.tolist(), input_values))

        out_node = BulkGridTensorIndexNode([lat_ax, lon_ax], out_unique_lats, out_lon_rows, out_flat_idx)
        out_node.result = out_results

        node.children.remove(in_node)
        in_node._parent = None
        node.add_child(out_node)
