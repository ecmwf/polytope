"""Grid interpolation / regridding support for Polytope feature extraction.

This module bridges Polytope's feature extraction (which fetches raw field
values for a set of native-grid points from GribJump) with ECMWF's `mir`
regridding engine, via `mir.WeightMatrix.from_feature_regrid`.

The idea is:

1. Build a sparse interpolation weight matrix between the datacube's native
   input grid (`in_grid`) and the user-requested output grid (`out_grid`),
   restricted to the output points that were actually requested
   (`out_indices`). `from_feature_regrid` keeps the matrix shape but zeroes
   out rows/columns we don't care about.
2. Inspect the matrix's sparsity structure (`scipy.sparse.csr_array.nonzero`)
   to find exactly which input-grid point indices have a non-zero weight for
   the requested output points. These are the *only* points we need to fetch
   from GribJump - this can be dramatically fewer than the full input grid.
3. Once GribJump has returned values for those input points, multiply them by
   the weight matrix (restricted/reordered to the fetched points) to produce
   interpolated values at the requested output points.

`mir` is an optional, heavy dependency (wraps the C++ MIR library), so it is
imported lazily and only required if interpolation is actually requested.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import numpy as np


class InterpolationNotAvailable(RuntimeError):
    """Raised when interpolation is requested but the `mir` package is not installed."""


def _import_mir():
    try:
        import mir  # noqa: F401
        from mir.weight_matrix import WeightMatrix

        return WeightMatrix
    except ImportError as e:
        raise InterpolationNotAvailable(
            "Interpolation was requested but the 'mir' python package is not installed. "
            "Install it to enable regridding support in Polytope."
        ) from e


def mapper_config_to_grid_spec(mapper_config) -> object:
    """Translate a Polytope `MapperConfig` (or a plain {"type": ..., "resolution": ...}
    dict describing the datacube's native grid) into a grid spec that
    `mir.Grid`/`WeightMatrix.from_regrid` can consume (a name string or a dict), e.g.:

        octahedral, resolution=1280        -> "O1280"
        reduced_gaussian, resolution=640    -> "N640"
        healpix, resolution=1024            -> "H1024_nested"
        regular, resolution=[0.1, 0.1]      -> {"grid": [0.1, 0.1]}
        unstructured/icon/lambert_conformal -> {"latitudes": [...], "longitudes": [...]}
                                                (built from the mapper's own point cloud)
    """
    if isinstance(mapper_config, dict):
        grid_type = mapper_config.get("type")
        resolution = mapper_config.get("resolution")
        points = mapper_config.get("points")
    else:
        grid_type = getattr(mapper_config, "type", None)
        resolution = getattr(mapper_config, "resolution", None)
        points = getattr(mapper_config, "points", None)

    if grid_type == "octahedral":
        return f"O{resolution}"
    if grid_type == "reduced_gaussian":
        return f"N{resolution}"
    if grid_type in ("healpix", "healpix_nested"):
        return f"H{resolution}_nested"
    if grid_type == "regular":
        if isinstance(resolution, (list, tuple)):
            dx, dy = resolution[0], resolution[-1]
        else:
            dx = dy = resolution
        return {"grid": [dx, dy]}
    if grid_type == "reduced_ll":
        # Reduced lat/lon grids don't have a simple named spec; fall back to
        # an explicit point list (see `grid_spec_from_points`).
        raise ValueError(
            "reduced_ll grids have no simple mir grid-spec name; " "use `grid_spec_from_points(lats, lons)` instead."
        )
    if grid_type in ("unstructured", "icon", "lambert_conformal"):
        if points:
            lats = [p[0] for p in points]
            lons = [p[1] for p in points]
            return grid_spec_from_points(lats, lons)
        raise ValueError(f"No explicit points available on mapper config for grid type '{grid_type}'")

    raise ValueError(f"Don't know how to build a mir grid spec for grid type '{grid_type}'")


def grid_spec_from_points(latitudes: Sequence[float], longitudes: Sequence[float]) -> Dict:
    """Build an explicit unstructured mir grid spec from a lat/lon point
    cloud, e.g. as returned by `grid_latlon_points()` on Polytope's irregular
    grid mappers.
    """
    return {"latitudes": list(latitudes), "longitudes": list(longitudes)}


class GridInterpolator:
    """Computes which native-grid points are needed to satisfy an
    interpolated request on an output grid, and performs the final
    interpolation once those points' values have been fetched.
    """

    def __init__(
        self,
        in_grid,
        out_grid,
        method: str = "linear",
        kwargs: Optional[Dict] = None,
        in_grid_desc: Optional[Dict] = None,
        out_grid_desc: Optional[Dict] = None,
    ):
        self.in_grid = in_grid
        self.out_grid = out_grid
        self.method = method
        self.kwargs = dict(kwargs or {})
        # Raw {"type": ..., "resolution": ...} descriptors, kept alongside the
        # mir-spec forms above so Polytope's own grid mappers can enumerate
        # the input/output grid points (see `grid_points.py`) without needing
        # to go back through mir.
        self.in_grid_desc = in_grid_desc
        self.out_grid_desc = out_grid_desc
        self._weight_matrix_cls = _import_mir()
        # Cache of (out_indices tuple) -> WeightMatrix, since computing the
        # weight matrix (an actual mir regrid Job) is comparatively expensive
        # and requests will often repeat the same output points per field.
        self._cache: Dict[Tuple[int, ...], object] = {}

    def _regrid_kwargs(self):
        kwargs = dict(self.kwargs)
        kwargs.setdefault("interpolation", self.method)
        return kwargs

    def weight_matrix_for(self, out_indices: Iterable[int] = ()):
        """Return (and cache) the WeightMatrix restricted to the given output
        grid point indices (all input points are kept for now; they get
        pruned down via `needed_input_indices`/`fetch_plan`).
        """
        key = tuple(sorted(set(out_indices)))
        if key not in self._cache:
            self._cache[key] = self._weight_matrix_cls.from_feature_regrid(
                self.in_grid,
                self.out_grid,
                out_indices=key,
                kwargs=self._regrid_kwargs(),
            )
        return self._cache[key]

    def needed_input_indices(self, out_indices: Iterable[int]) -> np.ndarray:
        """Given the output grid point indices actually requested, return the
        sorted, de-duplicated array of input grid point indices that have a
        non-zero interpolation weight for at least one of them. These are the
        *only* points that need to be fetched from GribJump.
        """
        wm = self.weight_matrix_for(out_indices)
        _, cols = wm.to_csr().nonzero()
        return np.unique(cols)

    def interpolate(
        self,
        out_indices: Sequence[int],
        input_values: Dict[int, float],
    ) -> np.ndarray:
        """Given raw values fetched from GribJump for (a subset of) input grid
        points, compute interpolated values for the requested output points.

        `input_values` maps input grid point index -> fetched value. Any
        input index required by the weight matrix but missing from
        `input_values` is treated as 0 (callers should ensure
        `needed_input_indices` was fully satisfied beforehand).
        """
        wm = self.weight_matrix_for(out_indices)
        csr = wm.to_csr()
        n_in = csr.shape[1]

        field = np.zeros(n_in, dtype=float)
        for idx, val in input_values.items():
            field[idx] = val

        result_full = csr @ field  # shape: (n_out_grid_points,)
        return result_full[list(out_indices)]

    def fetch_plan(self, out_indices: Sequence[int]) -> List[int]:
        """Convenience wrapper: the list of input grid point indices to query
        from GribJump in order to satisfy the given output points.
        """
        return self.needed_input_indices(out_indices).tolist()
