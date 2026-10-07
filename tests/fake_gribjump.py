"""A minimal in-memory stand-in for ``pygribjump.GribJump`` used to drive the real ``FDBDatacube`` in tests.

``axes()`` answers from a declared axis table and ``extract()`` returns one result per request, with ``values_flat``
(one contiguous float64 array over all of the request's index ranges) and the per-range ``values`` list of views
into it, as pygribjump 0.12 does.  Values are a deterministic function of the request path and the absolute grid
index, so any reordering or misassignment of values to tree nodes is detectable.

The iterator mirrors gribjump's own memory behaviour: every field's buffer is allocated before the first result is
handed out (``GribJump::extract`` wraps an already-materialised vector in its ``ExtractionIterator``), and the
iterator drops its own reference to each result as it yields it, so a consumer that releases a result frees its
buffer.
"""

import numpy as np


class _ExtractResult:
    """One field's extracted values, like ``pygribjump.ExtractionResult``."""

    def __init__(self, flat, shape, missing=False):
        self._flat = flat
        self._shape = shape
        self._missing = missing

    @property
    def values_flat(self):
        return self._flat

    @property
    def values(self):
        if self._missing:
            return []
        return np.split(self._flat, np.cumsum(self._shape)[:-1])


class _ExtractionIterator:
    """Cursor over results that were all built before the first ``next()``, as gribjump's ``VectorSource`` is."""

    def __init__(self, results):
        self._results = results

    def __iter__(self):
        for i in range(len(self._results)):
            result = self._results[i]
            self._results[i] = None  # hand over ownership, as VectorSource::next() does
            yield result


INDEX_SCALE = 1e8  # grid indices are below this, so ``value % INDEX_SCALE`` recovers the grid index


def path_offset(path):
    """Deterministic per-field offset derived from the (sorted) MARS request path."""
    key = ",".join(f"{k}={path[k]}" for k in sorted(path))
    digest = 0
    for ch in key:
        digest = (digest * 131 + ord(ch)) % 100_003
    return digest * INDEX_SCALE


def expected_value(path, index):
    """Value the fake returns for grid index ``index`` of the field identified by ``path``."""
    return path_offset(path) + np.asarray(index, dtype=np.float64)


def index_of(value):
    """Grid index encoded in a (non-NaN) value returned by the fake."""
    return np.rint(value % INDEX_SCALE).astype(np.int64).item()


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
                out.append(_ExtractResult(np.empty(0, dtype=np.float64), [], missing=True))
                continue
            shape = [end - start for start, end in ranges]
            flat = np.empty(sum(shape), dtype=np.float64)
            offset = 0
            for start, end in ranges:
                flat[offset : offset + end - start] = expected_value(path, np.arange(start, end))  # noqa: E203
                offset += end - start
            if self.nan_indices:
                offset = 0
                for start, end in ranges:
                    for i in range(start, end):
                        if i in self.nan_indices:
                            flat[offset + i - start] = np.nan
                    offset += end - start
            out.append(_ExtractResult(flat, shape))
        return _ExtractionIterator(out)
