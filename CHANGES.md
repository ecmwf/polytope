# Changes on `feat/numpy-leaf-values-pruned-get`

Notes for the PR description.

## Behaviour changes

- **Longitude leaf `values` are a float64 `np.ndarray`.** Leaves on the last (longitude) float axis built by the
  hull slicer hold a sorted float64 array instead of a tuple of Python floats. Iteration, indexing, `len`, `in`,
  `float(v)` and `tuple(values)` behave as before. Comparing a multi-point leaf with a tuple
  (`leaf.values == (0.0, 0.5)`) now gives an element-wise array, so code that compared against tuples must wrap
  the values in `tuple(...)` (three tests in this repo were updated). Non-leaf nodes, merged (lat, lon) nodes from
  the quadtree slicer and leaves on non-float axes keep tuples.
- **Leaf `result` is an `np.ndarray` after `FDBDatacube.get`.** float64 when every field was found; object dtype
  with `None` for missing fields otherwise (the values and `None`s are the same as in the old list).
  `leaf.result_array()` returns float64 with NaN for missing values. The xarray and mock backends are unchanged.
- **`FDBDatacube.get` returns the tree it filled** (it returned `None` before).
- **Missing field on a leaf spanning several index ranges.** When gribjump returned no data for a field and a
  leaf's grid indices were split into several ranges (e.g. a box across the longitude seam), every range appended
  `len(leaf.values)` `None`s, making the leaf's `result` too long and shifting the following fields. Each range now
  adds one `None` per point it covers. This can change CovJSON output for such requests (previously misaligned).
- The hull slicer no longer caches per-value remaps and per-line index lookups on the leaf (longitude) axis; this
  removes most of the slice-time memory (see `MEASUREMENTS.md`). Results are identical.

## New API

- `TensorIndexTree.prune(select=None, latitude_range=None, latitude_axis="latitude")`
- `TensorIndexTree.latitude_point_counts(select=None, latitude_axis="latitude")`
- `TensorIndexTree.result_array()` / `MergedTensorIndexNode.result_array()`
- `TensorIndexTree.add_values(values)`
- `FDBDatacube.get(requests, context=None, select=None, latitude_range=None)`
- `FDBDatacube.prepare(requests, context=None, select=None, latitude_range=None)`: runs every step of `get` before
  the gribjump call (pruning, nearest-point selection, grid-index lookup, de-duplication of grid points and
  reordering of longitude leaf `values` by grid index) without fetching data or touching `result`. After `prepare`
  the tree holds the exact coordinates, in order, that `get` fills, and `latitude_point_counts` counts the points
  `get` returns. Idempotent; `get` on a prepared tree or on `prepared.prune(select, latitude_range)` gives the same
  values/result order as `get` on the unprepared tree. Grid indices are recomputed by the later `get` rather than
  cached on the leaves, to keep the tree at ~8 B/point.
