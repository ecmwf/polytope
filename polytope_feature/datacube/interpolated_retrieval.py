"""Grid-interpolated retrieval.

When `self.datacube.interpolator` is set (ie. the "interpolation" Polytope
option was used), `Polytope.retrieve()` delegates to
`retrieve_interpolated()` instead of the normal slicing path for the grid
(lat/lon) axes:

1. The lat/lon shape(s) in the request (*any* shape: `Box`, `Disk`, `Polygon`,
   `Path`, `Union`, ... - not just bounding boxes) are sliced using
   Polytope's normal slicing mechanism (hullslicer/quadtree/point-in-polygon,
   whichever `engine_options` configures for lat/lon), but against the
   *output* grid rather than the datacube's native grid - see
   `OutputGridDatacube`. This gives the exact set of output grid points the
   shape selects, however irregular, using the same geometry-to-grid-point
   machinery as a normal (non-interpolated) request.
2. All other axes (date, time, step, levelist, ...) are sliced normally,
   against the real datacube, via the usual engines.
3. `GridInterpolator.needed_input_indices()` is used to work out exactly
   which *input* grid point indices are needed to interpolate those output
   points - this is typically a small fraction of the full input grid.
4. Those input-grid points are fetched from GribJump in a single batched
   request per sliced-axes leaf (via `BulkGridTensorIndexNode`, the same
   mechanism used by the `bulk_grid_leaves` option) - never as individual
   nearest-neighbour point queries.
5. Once fetched, the raw input-grid values are multiplied through the
   interpolation weight matrix and the input-grid bulk leaf is replaced by
   an output-grid bulk leaf holding the interpolated values and the
   corresponding *output* grid lat/lon coordinates - so the final tree only
   ever exposes output-grid points to the caller.

Grid point ordering assumption: the canonical point index produced by a
grid mapper's `unmap()` (used by Polytope/GribJump to address a field) is
assumed to match the native point ordering mir's weight matrix is built
against for the same grid type/resolution. This holds for the standard
ECMWF grid conventions (octahedral/reduced Gaussian/regular/healpix scanning
order) and is what makes it possible to avoid a per-point coordinate
round-trip through mir.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from typing import List, Tuple

import numpy as np

from . import grid_points
from .output_grid_datacube import OutputGridDatacube, build_output_grid_axis_options
from .tensor_index_tree import BulkGridTensorIndexNode


def _grid_axes_names(datacube) -> Tuple[str, str]:
    axes = datacube.grid_transformation.mapper_options.axes
    return axes[0], axes[1]


def _split_grid_shapes(request, grid_axes):
    """Split the request's shapes into those defined over the grid (lat/lon)
    axes and the rest. Any shape type is supported (Box, Disk, Polygon,
    Path, Union, ...).
    """
    grid_axes_set = set(grid_axes)
    grid_shapes = []
    remaining = []
    for shape in request.shapes:
        if set(shape.axes()) == grid_axes_set:
            grid_shapes.append(shape)
        else:
            remaining.append(shape)
    if len(grid_shapes) == 0:
        raise ValueError(f"Interpolation is enabled but the request has no shape over {grid_axes}")
    return grid_shapes, remaining


def _register_nearest_search(polytopes, nearest_search):
    for polytope in polytopes:
        if polytope.method == "nearest":
            query_points = polytope.values if polytope.is_flat else polytope.points
            points, _, tags = nearest_search.setdefault(tuple(polytope.axes()), ([], polytope.k, []))
            points.extend(list(pt) for pt in query_points)
            tags.extend([polytope.tag] * len(query_points))


def _collect_latlon_pairs(tree) -> List[Tuple[float, float]]:
    """Walk a sliced (root -> lat -> lon) tree and return every (lat, lon)
    pair it selects. Handles both compressed (multiple values per node) and
    uncompressed trees uniformly, by taking the cartesian product of each
    lat node's values with its lon children's values.
    """
    pairs = []
    for lat_node in tree.children:
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


def _slice_grid_shapes(polytope_engine, grid_shapes, out_grid_desc, datacube):
    """Slice the request's lat/lon shape(s) against the *output* grid using
    Polytope's normal slicing mechanism, and return the set of output grid
    points selected as (unique_lats, lon_rows, flat_indices).
    """
    axis_options, grid_axes = build_output_grid_axis_options(datacube, out_grid_desc)
    output_datacube = OutputGridDatacube(axis_options)

    grid_polytopes = []
    for shape in grid_shapes:
        grid_polytopes.extend(shape.polytope())
    _register_nearest_search(grid_polytopes, output_datacube.nearest_search)

    output_tree = polytope_engine.slice(output_datacube, grid_polytopes)

    if len(output_datacube.nearest_search) > 0 and len(output_tree.children) > 0:
        output_datacube.nearest_lat_lon_search(output_tree)

    pairs = _collect_latlon_pairs(output_tree)
    if len(pairs) == 0:
        raise ValueError("The requested output grid area does not contain any output grid points")

    out_mapper = grid_points.grid_spec_to_mapper(out_grid_desc)
    return _pairs_to_rows(out_mapper, pairs)


def _replace_with_interpolated_leaf(leaf, interpolator, out_unique_lats, out_lon_rows, out_flat_idx, lat_ax, lon_ax):
    """Given a leaf whose only child is the input-grid `BulkGridTensorIndexNode`
    populated by `datacube.get()`, interpolate its fetched values onto the
    output grid and replace it in-place with an output-grid bulk leaf.
    """
    in_node = leaf.children[0]
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

    leaf.children.remove(in_node)
    in_node._parent = None
    leaf.add_child(out_node)
    return out_node


def retrieve_interpolated(polytope_engine, request):
    """Implements `Polytope.retrieve()` when `datacube.interpolator` is set."""
    datacube = polytope_engine.datacube
    interpolator = datacube.interpolator

    grid_axes = _grid_axes_names(datacube)
    grid_shapes, remaining_shapes = _split_grid_shapes(request, grid_axes)

    # 1. Slice the lat/lon shape(s) against the *output* grid, using Polytope's normal
    #    slicing mechanism (works for any shape, not just bounding boxes).
    out_unique_lats, out_lon_rows, out_flat_idx = _slice_grid_shapes(
        polytope_engine, grid_shapes, interpolator.out_grid_desc, datacube
    )

    # 2. Input grid points actually needed to interpolate those output points.
    needed_in_idx = interpolator.needed_input_indices(out_flat_idx.tolist())
    in_mapper = grid_points.grid_spec_to_mapper(interpolator.in_grid_desc)
    in_lats, in_lons = grid_points.latlon_for_indices(in_mapper, needed_in_idx)
    in_unique_lats, in_lon_rows, in_flat_idx = grid_points.group_rows(in_lats, in_lons, needed_in_idx)

    logging.info(
        "Interpolation: %d output grid point(s) requested, needing %d input grid point(s)",
        len(out_flat_idx),
        len(in_flat_idx),
    )

    lat_ax = datacube._axes[grid_axes[0]]
    lon_ax = datacube._axes[grid_axes[1]]

    # 3. Slice every other axis normally, against the real datacube; the grid axes are
    #    handled above instead.
    datacube.check_branching_axes(request)
    polytope_engine.switch_polytope_dim(request)
    datacube.nearest_search = {}

    remaining_polytopes = []
    for shape in remaining_shapes:
        remaining_polytopes.extend(shape.polytope())
    _register_nearest_search(remaining_polytopes, datacube.nearest_search)

    request_tree = polytope_engine.slice(datacube, remaining_polytopes, exclude_axes=set(grid_axes))

    # 4. Attach one input-grid bulk leaf per sliced-axes combination.
    leaves = request_tree.leaves
    for leaf in leaves:
        in_node = BulkGridTensorIndexNode([lat_ax, lon_ax], in_unique_lats, in_lon_rows, in_flat_idx)
        leaf.add_child(in_node)

    datacube.get(request_tree, polytope_engine.context)

    # 5. Interpolate each leaf's fetched values and replace the input-grid bulk leaf
    #    with an output-grid bulk leaf.
    for leaf in leaves:
        _replace_with_interpolated_leaf(leaf, interpolator, out_unique_lats, out_lon_rows, out_flat_idx, lat_ax, lon_ax)

    return request_tree
