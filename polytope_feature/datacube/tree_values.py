"""Helpers for ``TensorIndexTree`` node ``values`` that may be either a tuple or a 1-D ``np.ndarray``.

Non-leaf nodes keep their values as small hashable tuples.  Leaf nodes on the last (longitude) axis built by the
hull slicer store their values as a float64 ``np.ndarray`` (~8 B/point instead of ~32 B/point for a tuple of
Python floats).  These helpers give both representations the same ordering, equality and hashing semantics that
the tuple representation always had.
"""

import numpy as np


def is_array(values):
    return isinstance(values, np.ndarray)


def values_identical(a, b):
    """Exact element-wise equality, equivalent to ``a == b`` for two tuples."""
    if not is_array(a) and not is_array(b):
        return a == b
    if len(a) != len(b):
        return False
    return bool(np.array_equal(np.asarray(a), np.asarray(b)))


def values_within_tol(a, b, tol):
    """True unless some pair of elements differs by more than ``tol`` (NaN never counts as a difference)."""
    diff = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
    return not bool(np.any(diff > tol))


def values_lt(a, b):
    """Lexicographic ``a < b``, equivalent to tuple comparison."""
    if not is_array(a) and not is_array(b):
        return a < b
    a = np.asarray(a)
    b = np.asarray(b)
    n = min(len(a), len(b))
    differing = np.flatnonzero(a[:n] != b[:n])
    if differing.size:
        i = differing[0]
        return bool(a[i] < b[i])
    return len(a) < len(b)


def values_hash_key(values):
    """A hashable key equal to the tuple of the same values (so tuple and array nodes hash alike)."""
    if is_array(values):
        return tuple(values.tolist())
    return values


def take(values, positions):
    """Select ``positions`` from ``values``, preserving the container type."""
    if is_array(values):
        return values[np.asarray(positions, dtype=np.intp)]
    return tuple(values[k] for k in positions)


def remove_value(values, value):
    """Drop every element equal to ``value``, preserving the container type."""
    if is_array(values):
        return values[values != value]
    return tuple(val for val in values if val != value)


def merge_sorted(values, new_values):
    """Return ``values`` extended with ``new_values`` and sorted, as a float64 array."""
    combined = np.concatenate([np.asarray(values, dtype=np.float64), np.asarray(new_values, dtype=np.float64)])
    return np.sort(combined, kind="stable")


def result_as_array(result):
    """Return a leaf ``result`` as a float64 array, with missing (``None``) values as NaN."""
    if is_array(result) and result.dtype != object:
        return result.astype(np.float64, copy=False)
    return np.array([np.nan if v is None else v for v in result], dtype=np.float64)


def finalise_result(chunks):
    """Concatenate per-range result chunks into the leaf ``result`` array.

    ``chunks`` is a list whose items are either array-likes of values or lists of ``None`` (a field that gribjump
    did not find).  When every chunk holds values the result is a float64 array; when some chunk is missing the
    result is an object array holding ``None`` for the missing values, exactly as the list-based results did.
    """
    if not chunks:
        return np.empty(0, dtype=np.float64)
    has_missing = any(isinstance(c, list) and any(v is None for v in c) for c in chunks)
    if not has_missing:
        return np.concatenate([np.asarray(c, dtype=np.float64) for c in chunks])
    out = np.empty(sum(len(c) for c in chunks), dtype=object)
    start = 0
    for c in chunks:
        end = start + len(c)
        if isinstance(c, list):
            out[start:end] = c
        else:
            # keep numpy scalars, as the list-based results did
            out[start:end] = list(np.asarray(c, dtype=np.float64))
        start = end
    return out
