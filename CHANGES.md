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
- **Regular and local_regular grid index lookup is O(log n) per point.** `RegularGridMapper.unmap` rebuilt and
  scanned the whole longitude list twice per point (`get`/`prepare` on a global 0.25° box took 217 s); it now uses
  `np.searchsorted` on axis arrays built once per mapper, and `LocalRegularGridMapper.unmap`'s nearest-neighbour
  step is vectorised. Indices are identical (checked against the old code on random points of several grids),
  including the `IndexError` for values more than 1e-8 off the grid. See `MEASUREMENTS.md`.
- **Nearest-point search no longer mutates the request points.** For a `Point(["longitude", "latitude"], ...,
  method="nearest")` the stored points were swapped in place on every search, so the next branch of the same `get`
  (e.g. a second realization or param on a datacube that does not compress them) or the next `get`/`prepare`
  searched near the flipped coordinates. A copy is swapped now. Requests with (latitude, longitude) axes, as
  polytope-mars builds by default, are unaffected; (longitude, latitude) position requests over several
  uncompressed branches return different (now correct) points.
- **One gribjump result is read once, as one flat buffer.** `assign_fdb_output_to_nodes` took `result.values[i]`
  per index range -- a numpy object plus a list slot each -- and kept the chunks of every leaf of the call until
  the last field had arrived. It now takes `result.values_flat` once per field and scatters it into the leaves by
  a plan built per spatial sub-tree (`datacube/fdb_assign.py`), and a leaf's result for the whole call is
  pre-allocated (`n_points x n_fields`, float64, NaN-filled) and filled field by field. Values, point order,
  the object/`None` result of a missing field and the value order of merged polygon rows are unchanged
  (`tests/test_flat_assign.py` compares every scenario against the old implementation, kept in
  `tests/legacy_assign.py`). On grids whose points a bounding box covers in long runs (regular, octahedral,
  local_regular) nothing changes measurably; on HEALPix nested grids, where a box breaks into roughly one range
  per 1.6 points, the peak of a 12-field `get` falls from ~370 to ~40 B/value. See `MEASUREMENTS.md`.

## Opt-in: one longitude leaf per latitude node for polygons and paths

`Polytope._merge_union_rows` (private class attribute, **default `False`**; set it on a `Polytope` instance before
slicing). Unions of non-orthogonal shapes (the triangles of a `Polygon`, the segments of a `Path`) left the leaf
(longitude) axis uncompressed, so every point was its own tree node (~1.3-1.4 KB/point, see `MEASUREMENTS.md`).
With the switch on, and when all pieces carry the same tag, the leaf axis stays compressed and the pieces' leaves
under each latitude node are merged into one sorted, de-duplicated float64 array (`datacube/tree_rows.py`).

- The flattened (latitude, longitude) point sequence is identical to the per-point tree, and so are `get`,
  `prepare`, `prune` and `latitude_point_counts` results (`tests/test_polygon_rows.py`, regular / HEALPix nested
  128 / O1280, notched and seam-crossing polygons, missing fields, bands).
- Merged leaves are flagged (`_keep_value_order`) so `get`/`prepare` keep their values ascending rather than
  reordering them by grid index as for box leaves, and put the results (fetched in index order) back into value
  order. On HEALPix nested grids this keeps the per-point (longitude) order instead of nested-index order.
- Leaf tags: a merged leaf carries the (single) tag of the pieces, as each per-point leaf did. Unions whose pieces
  have different tags keep one leaf per point.
- Tree structure changes: `len(tree.leaves)` counts rows, not points; code counting points must sum
  `len(leaf.values)`.
- **Why it is off:** covjsonkit's legacy `walk_tree_step` (`from_polytope_step`, used for climate-dt and `ng`
  polygon and timeseries requests) slices each leaf's `result` assuming one point per leaf. With the switch on, the
  polytope-mars golden cases `cdt_polygon_sfc` and `cdt_polygon_single_param` change (fewer values per range);
  every other golden case, including `efas_polygon_fc` and `o1280_trajectory`, stays byte-identical. Turn it on
  once the polytope-mars block walker replaces the legacy walk for those requests.

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
- `FDBDatacube.get_iter(requests, context=None, select=None, latitude_range=None)`: builds the same gribjump call
  as `get` (same pruning, same requests, same order) but yields `(field_path, [(leaf, values), ...])` per field
  instead of filling the tree, so that a caller can hold one field (or one group) at a time. `field_path` is the
  MARS keys of one field with one scalar value each, in the order the tree descends; `values` is a fresh float64
  array of `len(leaf.values)` points, NaN where bitmap-missing, and the leaves come in tree order, so
  concatenating them gives the field's points in the order `get` writes them. The second item is `None` for a
  field gribjump has no message for (what `get` records as `None` values), so a missing field is detectable
  without reading a value. Fields arrive in gribjump's request order: sub-trees in tree order, then the
  cartesian product of the sub-tree's compressed axes in tree order, outermost axis first and innermost varying
  fastest -- the order in which `get` lays a leaf's fields out in its `result`. Nothing is written to any
  `result`: the tree is left as `prepare` leaves it, and the caller owns the arrays. Nothing is requested until
  the first item is consumed.

## Follow-ups (not in this branch)

- **The request side still costs ~90-210 B/value.** `get_last_layer_before_leaf` collects every point's grid
  index as a Python `int` in a list per leaf, and `sort_fdb_request_ranges` then sorts `enumerate(...)` of those
  lists, which builds one tuple per point. After the result side was fixed this is what a `get` peaks on
  (`MEASUREMENTS.md`): ~90 B/value for one field on the EFAS Danube box, ~210 B/value on a HEALPix 1024 Europe
  box. Both passes are expressible in numpy over the leaf's index array (the mappers already return arrays),
  which would leave only the request ranges themselves.
- **`extract_from_mask` / `extract_from_indices` would not help by themselves.** Both are pure client-side
  conveniences in pygribjump 0.12: they build the same `ExtractionRequest` list the current `extract` call
  builds, so the bytes on the wire, the grid-hash check and the server's work are identical and nothing needs
  validating against the remote gribjump server beyond what `extract` already does. `extract_from_mask` derives
  the ranges from a boolean mask in numpy (attractive: one mask could be shared by every field of a call, and
  its ranges are exactly the ascending, de-duplicated ranges we already send), but `ExtractionRequest.__init__`
  then copies the range list and builds a Python list of range lengths per *field*, so the per-range Python
  objects reappear inside pygribjump; and `extract_from_indices` is strictly worse, since it asks for one range
  per point (357k ranges instead of 224k for the HEALPix box above, as a list of tuples per field).
  Removing the last per-range objects therefore needs pygribjump to accept the ranges (or the mask) as a numpy
  array it passes straight to C, not a different call on our side. What *would* need validating if a mask is
  ever used: the mask must span the whole field (`numberOfValues` of the grid, not of the request), so the grid
  size would have to come from the mapper and agree with the `gridHash` the server checks.
