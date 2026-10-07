"""A minimal in-memory stand-in for ``pygribjump.GribJump`` used to drive the real ``FDBDatacube`` in tests.

``axes()`` answers from a declared axis table and ``extract()`` returns, per request, one ``np.ndarray`` per
requested index range.  Values are a deterministic function of the request path and the absolute grid index, so
any reordering or misassignment of values to tree nodes is detectable.
"""

import numpy as np


class _ExtractResult:
    def __init__(self, values):
        self.values = values


INDEX_SCALE = 1e8  # grid indices are below this, so ``value % INDEX_SCALE`` recovers the grid index


def path_offset(path):
    """Deterministic per-field offset derived from the (sorted) MARS request path."""
    key = ",".join(f"{k}={path[k]}" for k in sorted(path))
    digest = 0
    for ch in key:
        digest = (digest * 131 + ord(ch)) % 100_003
    return float(digest) * INDEX_SCALE


def expected_value(path, index):
    """Value the fake returns for grid index ``index`` of the field identified by ``path``."""
    return path_offset(path) + np.asarray(index, dtype=np.float64)


def index_of(value):
    """Grid index encoded in a (non-NaN) value returned by the fake."""
    return int(round(value % INDEX_SCALE))


class GribJump:
    """Fake gribjump. The class name must be ``GribJump`` so ``Datacube.create`` picks the FDB backend."""

    def __init__(self, axes, missing=None, nan_indices=None):
        # axes: dict axis name -> list of string values
        self.axes_table = {k: list(v) for k, v in axes.items()}
        # missing: list of partial paths (dicts); a request matching any of them yields an empty result
        self.missing = list(missing or [])
        # nan_indices: grid indices that are bitmap-missing (NaN) in every field
        self.nan_indices = set(nan_indices or [])
        self.extract_calls = []

    def axes(self, partial_request, ctx=None):
        return {k: list(v) for k, v in self.axes_table.items()}

    def _is_missing(self, path):
        for m in self.missing:
            if all(str(path.get(k)) == str(v) for k, v in m.items()):
                return True
        return False

    def extract(self, requests, ctx=None):
        self.extract_calls.append(requests)
        out = []
        for path, ranges, _md5 in requests:
            if self._is_missing(path):
                out.append(_ExtractResult([]))
                continue
            vals = []
            for start, end in ranges:
                arr = expected_value(path, np.arange(start, end))
                if self.nan_indices:
                    for i in range(start, end):
                        if i in self.nan_indices:
                            arr[i - start] = np.nan
                vals.append(arr)
            out.append(_ExtractResult(vals))
        return iter(out)
