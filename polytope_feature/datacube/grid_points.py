"""Grid-point lookup helpers used by interpolation/regridding.

All of the actual per-grid-type math (ring sizes, longitude offsets, point
ordering, ...) lives on the mapper classes themselves (see
`transformations/datacube_mappers/mapper_types/*.py`); this module just
builds mappers from a plain `{"type": ..., "resolution": ...}` spec and
provides a generic, grid-type-agnostic way to convert canonical grid-point
indices back to (lat, lon).
"""

from __future__ import annotations

from typing import List, Tuple

import numpy as np

from ..options import MapperConfig
from .transformations.datacube_mappers.datacube_mappers import DatacubeMapper


def grid_spec_to_mapper(grid_desc):
    """Build a concrete grid mapper (eg. `OctahedralGridMapper`, `ICONGridMapper`, ...)
    from a plain grid spec dict, reusing the same `DatacubeMapper`/
    `DatacubeAxisTransformation.get_final_axes` machinery a real datacube uses to build
    its own grid axes - so every grid type (structured or irregular) Polytope already
    understands is supported here too, with no extra dispatch logic of its own.

    `grid_desc` eg.:
        {"type": "octahedral", "resolution": 1280}
        {"type": "healpix_nested", "resolution": 1024}
        {"type": "icon", "uuid": "..."}
        {"type": "unstructured", "points": [(lat, lon), ...]}
    """
    if not isinstance(grid_desc, dict) or "type" not in grid_desc:
        raise ValueError(
            "Grid spec must be a dict with at least a 'type' key " "(e.g. {'type': 'octahedral', 'resolution': 1280})"
        )
    mapper_config = MapperConfig(
        name="mapper",
        type=grid_desc["type"],
        resolution=grid_desc.get("resolution"),
        axes=["latitude", "longitude"],
        uuid=grid_desc.get("uuid"),
        points=grid_desc.get("points"),
    )
    wrapper = DatacubeMapper(name="values", mapper_options=mapper_config)
    return wrapper._final_transformation


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


class RingIndex:
    """Converts canonical grid-point indices back to (lat, lon), in
    O(log num_rings) time per index for "ring" grid types (octahedral,
    regular, healpix, reduced_gaussian, nested healpix) and O(1) for
    point-cloud grid types (unstructured, icon, lambert_conformal) - without
    ever enumerating/materializing the whole grid.

    Each mapper type supplies its own `ring_size(ring_idx)`/
    `ring_lon_start(ring_idx)` (ring types) or `latlon_for_indices(indices)`
    (point-cloud types); this class only does the generic
    index-to-ring/offset bookkeeping.
    """

    def __init__(self, mapper):
        self.mapper = mapper
        self._point_cloud = hasattr(mapper, "latlon_for_indices")
        if not self._point_cloud:
            self.lats = np.asarray(mapper.first_axis_vals(), dtype=np.float64)
            self.sizes = np.array([mapper.ring_size(i) for i in range(len(self.lats))], dtype=np.int64)
            self.offsets = np.concatenate([[0], np.cumsum(self.sizes)])

    @property
    def total_points(self) -> int:
        if self._point_cloud:
            return self.mapper.point_count()
        return int(self.offsets[-1])

    def latlon_for_indices(self, indices) -> Tuple[np.ndarray, np.ndarray]:
        indices = np.asarray(indices, dtype=np.int64)
        if len(indices) == 0:
            return np.empty(0), np.empty(0)
        if indices.min() < 0 or indices.max() >= self.total_points:
            raise ValueError("Grid point index out of range for this grid mapper")

        if self._point_cloud:
            return self.mapper.latlon_for_indices(indices)

        remap = getattr(self.mapper, "remap_canonical_index", None)
        ring_major = remap(indices) if remap is not None else indices

        ring_idx = np.searchsorted(self.offsets, ring_major, side="right") - 1
        pos_in_ring = ring_major - self.offsets[ring_idx]
        lats = self.lats[ring_idx]
        lons = np.empty(len(indices), dtype=np.float64)

        # Group by ring so the (cheap) per-ring spacing/start lookup is only done once per
        # distinct ring touched, rather than once per point.
        for ring in np.unique(ring_idx):
            mask = ring_idx == ring
            size = int(self.sizes[ring])
            spacing = 360.0 / size
            start = self.mapper.ring_lon_start(int(ring))
            lons[mask] = start + pos_in_ring[mask] * spacing
        return lats, lons


def latlon_for_indices(mapper, indices) -> Tuple[np.ndarray, np.ndarray]:
    """Return (lats, lons) for the given canonical grid-point indices."""
    return RingIndex(mapper).latlon_for_indices(indices)
