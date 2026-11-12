"""Generic grid-point enumeration, built directly on top of Polytope's own
`DatacubeMapper` grid-type implementations (octahedral, healpix, regular,
reduced_gaussian, ...).

This is used to support interpolation/regridding: we need to enumerate the
output grid's (lat, lon) points in the grid's *canonical* native order (the
same order used to compute FDB/GribJump field indices for the input grid),
and to work out which canonical indices fall within a requested lat/lon
bounding box - for both the input grid (what polytope already does via the
normal slicing path) and, newly, for the output grid (which has no backing
datacube/axes of its own).

All concrete mapper type implementations share the same interface
(`first_axis_vals`, `map_first_axis`, `second_axis_vals`, `map_second_axis`,
`unmap`), so a single generic implementation here works for every grid type
without needing a full `Datacube`/axis machinery.
"""

from __future__ import annotations

from importlib import import_module
from typing import List, Tuple

import numpy as np

from .transformations.datacube_mappers.datacube_mappers import (
    _type_to_datacube_mapper_lookup,
)


def _mapper_module_name(grid_type: str) -> str:
    # Mirrors DatacubeMapper.generate_final_transformation()'s module lookup.
    if grid_type in ("unstructured", "icon", "lambert_conformal"):
        return "irregular"
    if grid_type == "healpix_nested":
        return "nested_healpix"
    if grid_type == "reduced_ll":
        return "reduced_ll"
    if grid_type == "local_regular":
        return "local_regular"
    return grid_type


def build_bare_mapper(grid_type: str, resolution):
    """Instantiate a concrete grid mapper (e.g. `OctahedralGridMapper`) for a
    given grid type/resolution, without needing a backing `Datacube`/axis.
    """
    if grid_type not in _type_to_datacube_mapper_lookup:
        raise ValueError(f"Unknown/unsupported grid type '{grid_type}' for output-grid enumeration")
    class_name = _type_to_datacube_mapper_lookup[grid_type]
    if class_name == "IrregularGridMapper" or class_name == "NestedHealpixGridMapper":
        raise NotImplementedError(
            f"Grid type '{grid_type}' has no simple canonical ordering usable for output-grid "
            "interpolation; please provide an explicit point list instead."
        )
    module = import_module(
        f"polytope_feature.datacube.transformations.datacube_mappers.mapper_types." f"{_mapper_module_name(grid_type)}"
    )
    mapper_cls = getattr(module, class_name)
    return mapper_cls(
        base_axis="latitude",
        mapped_axes=["latitude", "longitude"],
        resolution=resolution,
    )


def grid_spec_to_mapper(grid_spec):
    """Build a bare mapper from an interpolation grid spec dict, e.g.:
    {"type": "octahedral", "resolution": 1280}
    {"type": "regular", "resolution": [0.1, 0.1]}
    """
    if isinstance(grid_spec, dict) and "type" in grid_spec:
        return build_bare_mapper(grid_spec["type"], grid_spec.get("resolution"))
    raise ValueError(
        "Output grid spec must be a dict with a 'type' and 'resolution' key "
        "(e.g. {'type': 'octahedral', 'resolution': 1280}) to enumerate its points."
    )


def _ring_sizes(mapper) -> np.ndarray:
    """Cheap, closed-form per-ring point counts.

    Unlike calling `second_axis_vals()` for every ring (which materializes a
    full list of longitudes per ring, ie. the whole grid), these are O(1) or
    O(num_rings) formulas already used internally by each mapper type, so this
    costs O(num_rings) total rather than O(num_points) - essential for large
    grids (eg. O1280 has ~2560 rings but ~6.6M points).
    """
    cls_name = type(mapper).__name__
    n_rings = len(mapper.first_axis_vals())

    if cls_name == "RegularGridMapper":
        # Every ring has the same number of points.
        return np.full(n_rings, 4 * mapper._resolution, dtype=np.int64)

    if cls_name == "OctahedralGridMapper":
        sizes = np.empty(n_rings, dtype=np.int64)
        for i, lat in enumerate(mapper._first_axis_vals):
            spacing, _ = mapper.second_axis_spacing([lat])
            sizes[i] = round(360.0 / spacing)
        return sizes

    if cls_name == "HealpixGridMapper":
        return np.array([mapper.HEALPix_nj(i) for i in range(n_rings)], dtype=np.int64)

    if cls_name == "ReducedGaussianGridMapper":
        return np.asarray(mapper.lon_spacing(), dtype=np.int64)

    # Fallback for any other mapper type: no cheap formula known, so fall back
    # to materializing each ring's longitude list (still only O(num_points)
    # once, same as before, but at least not duplicated by also calling unmap()).
    return np.array([len(mapper.second_axis_vals([lat])) for lat in mapper.first_axis_vals()], dtype=np.int64)


def _ring_lon_start(mapper, ring_idx: int) -> float:
    """Longitude of the first point in a ring (0.0 for every grid type except
    healpix, whose polar-cap/odd rings are offset by half a step).
    """
    if type(mapper).__name__ == "HealpixGridMapper":
        nj = mapper.HEALPix_nj(ring_idx)
        step = 360.0 / nj
        resolution = mapper._resolution
        if ring_idx < resolution or 3 * resolution - 1 < ring_idx or (ring_idx + resolution) % 2:
            return step / 2.0
        return 0.0
    return 0.0


class RingIndex:
    """Caches a grid mapper's per-ring offsets so that arbitrary canonical
    point indices can be converted back to (lat, lon) in O(log num_rings)
    time, without enumerating the whole grid.

    Construction is O(num_rings) (a few thousand for the largest operational
    grids); each lookup thereafter is O(log num_rings) regardless of how many
    points the grid has in total.
    """

    def __init__(self, mapper):
        self.mapper = mapper
        self.lats = np.asarray(mapper.first_axis_vals(), dtype=np.float64)
        self.sizes = _ring_sizes(mapper)
        self.offsets = np.concatenate([[0], np.cumsum(self.sizes)])

    @property
    def total_points(self) -> int:
        return int(self.offsets[-1])

    def latlon_for_indices(self, indices) -> Tuple[np.ndarray, np.ndarray]:
        indices = np.asarray(indices, dtype=np.int64)
        if len(indices) == 0:
            return np.empty(0), np.empty(0)
        if indices.min() < 0 or indices.max() >= self.total_points:
            raise ValueError("Grid point index out of range for this grid mapper")

        ring_idx = np.searchsorted(self.offsets, indices, side="right") - 1
        pos_in_ring = indices - self.offsets[ring_idx]
        lats = self.lats[ring_idx]
        lons = np.empty(len(indices), dtype=np.float64)

        # Group by ring so the (cheap) per-ring spacing/start lookup is only done once per
        # distinct ring touched, rather than once per point.
        for ring in np.unique(ring_idx):
            mask = ring_idx == ring
            size = int(self.sizes[ring])
            spacing = 360.0 / size
            start = _ring_lon_start(self.mapper, int(ring))
            lons[mask] = start + pos_in_ring[mask] * spacing
        return lats, lons


def enumerate_all_points(mapper) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (lats, lons, indices) for every point of the grid, in canonical
    (ascending index) order.

    This materializes the whole grid (O(num_points)) and is mainly useful for
    small grids/testing; for looking up a handful of specific indices on a
    large grid, use `latlon_for_indices` (backed by `RingIndex`) instead.
    """
    lats_out: List[float] = []
    lons_out: List[float] = []
    idxs_out: List[int] = []
    for lat in mapper.first_axis_vals():
        lons = mapper.second_axis_vals([lat])
        idxs = mapper.unmap([lat], lons)
        lats_out.extend([lat] * len(lons))
        lons_out.extend(lons)
        idxs_out.extend(idxs)
    order = np.argsort(idxs_out)
    return (
        np.asarray(lats_out)[order],
        np.asarray(lons_out)[order],
        np.asarray(idxs_out)[order],
    )


def points_in_bbox(mapper, north, south, east, west) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return (lats, lons, indices) of all grid points within
    [south, north] x [west, east], in canonical (ascending index) order.
    """
    lats_out: List[float] = []
    lons_out: List[float] = []
    idxs_out: List[int] = []
    for lat in mapper.map_first_axis(south, north):
        lons = mapper.map_second_axis([lat], west, east)
        if len(lons) == 0:
            continue
        idxs = mapper.unmap([lat], lons)
        lats_out.extend([lat] * len(lons))
        lons_out.extend(lons)
        idxs_out.extend(idxs)
    order = np.argsort(idxs_out)
    return (
        np.asarray(lats_out)[order],
        np.asarray(lons_out)[order],
        np.asarray(idxs_out)[order],
    )


def latlon_for_indices(mapper, indices) -> Tuple[np.ndarray, np.ndarray]:
    """Return (lats, lons) for the given canonical grid-point indices.

    Backed by `RingIndex`: O(num_rings) one-off setup plus O(log num_rings)
    per index, rather than enumerating the whole grid - this is what keeps
    interpolation fast for very large grids (eg. O1280's ~6.6M points, but
    only ~2560 rings).
    """
    return RingIndex(mapper).latlon_for_indices(indices)


def group_rows(
    lats: np.ndarray, lons: np.ndarray, indices: np.ndarray
) -> Tuple[np.ndarray, List[np.ndarray], np.ndarray]:
    """Group (lat, lon, index) point triples into latitude-major rows, as
    needed to build a `BulkGridTensorIndexNode` (one row per distinct
    latitude, with that row's longitudes/indices in ascending longitude
    order). Returns (unique_lats, lon_rows, flat_indices), where
    `flat_indices` is in the same row-major flattened order as
    `np.concatenate(lon_rows)`.
    """
    lats = np.asarray(lats)
    lons = np.asarray(lons)
    indices = np.asarray(indices)
    if len(lats) == 0:
        return np.empty(0), [], np.empty(0, dtype=np.int64)

    order = np.lexsort((lons, lats))
    sorted_lats = lats[order]
    sorted_lons = lons[order]
    sorted_idx = indices[order]

    unique_lats, start_positions = np.unique(sorted_lats, return_index=True)
    lon_rows = np.split(sorted_lons, start_positions[1:])
    idx_rows = np.split(sorted_idx, start_positions[1:])
    flat_indices = np.concatenate(idx_rows) if len(idx_rows) else np.empty(0, dtype=np.int64)
    return unique_lats, lon_rows, flat_indices
