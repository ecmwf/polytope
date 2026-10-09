# Changes on `feat/numpy-leaf-values-pruned-get`

`feat/fix_tags_and_nearest_point` (`918580e3`, four commits) is merged into this branch; the merge and what it
changes are described under "Merged: bulk spatial nodes and per-point tags" below.

## Behaviour changes

- **Longitude leaf `values` are a float64 `np.ndarray`.** Leaves on the last (longitude) float axis built by the
  hull slicer hold a sorted float64 array instead of a tuple of Python floats. Iteration, indexing, `len`, `in`,
  `float(v)` and `tuple(values)` behave as before. Comparing a multi-point leaf with a tuple
  (`leaf.values == (0.0, 0.5)`) now gives an element-wise array, so code that compared against tuples must wrap
  the values in `tuple(...)` (three tests in this repo were updated). Non-leaf nodes, merged (lat, lon) nodes from
  the quadtree slicer and leaves on non-float axes keep tuples.
- **Leaf `result` is an `np.ndarray` after `FDBDatacube.get`.** float64 when every field was found; object dtype
  with `None` for missing fields otherwise (the values and `None`s are those of the list it replaces).
  `leaf.result_array()` returns float64 with NaN for missing values. The xarray and mock backends are unchanged.
- **`FDBDatacube.get` returns the tree it filled** (it returned `None` before).
- **Missing field on a leaf spanning several index ranges.** When gribjump returned no data for a field and a
  leaf's grid indices were split into several ranges (e.g. a box across the longitude seam), every range appended
  `len(leaf.values)` `None`s, making the leaf's `result` too long and shifting the following fields. Each range now
  adds one `None` per point it covers. This changes CovJSON output for such requests, where the values after a
  missing field were shifted.
- The hull slicer does not cache per-value remaps or per-line index lookups on the leaf (longitude) axis, which
  removes most of the slice-time memory (see `MEASUREMENTS.md`). Results are identical.
- **Regular and local_regular grid index lookup is O(log n) per point.** `RegularGridMapper.unmap` rebuilt and
  scanned the whole longitude list twice per point (`get`/`prepare` on a global 0.25° box took 217 s); it now uses
  `np.searchsorted` on axis arrays built once per mapper, and `LocalRegularGridMapper.unmap`'s nearest-neighbour
  step is vectorised. Indices are identical (checked against the scanning implementation on random points of
  several grids),
  including the `IndexError` for values more than 1e-8 off the grid. See `MEASUREMENTS.md`.
- **Nearest-point search leaves the registered request points unchanged.** For a `Point(["longitude", "latitude"], ...,
  method="nearest")` the stored points were swapped in place on every search, so the next branch of the same `get`
  (e.g. a second realization or param on a datacube that does not compress them) or the next `get`/`prepare`
  searched near the flipped coordinates. A copy is swapped now. Requests with (latitude, longitude) axes, as
  polytope-mars builds by default, are unaffected; (longitude, latitude) position requests over several
  uncompressed branches return the points nearest to each query, which differs from what they returned before.
- **One gribjump result is read once, as one flat buffer.** `assign_fdb_output_to_nodes` took `result.values[i]`
  per index range -- a numpy object plus a list slot each -- and kept the chunks of every leaf of the call until
  the last field had arrived. It takes `result.values_flat` once per field and scatters it into the spatial
  node's point order. Values, point order and the object/`None` result of a missing field are unchanged. On
  grids whose points a bounding box covers in long runs (regular, octahedral, local_regular) nothing changes
  measurably; on HEALPix nested grids, where a box breaks into roughly one range per 1.6 points, the peak of a
  12-field `get` falls from ~370 to ~40 B/value. See `MEASUREMENTS.md`.
- **HEALPix nested grid index lookup is vectorised.** `NestedHealpixGridMapper.unmap` called the Rust extension,
  which resolves one point at a time (~14 us per point, and superlinear in the points of a ring: 6.0 ms for a
  430-point ring of HEALPix 1024, 122 ms for a full 4,096-point ring); that was what `prepare`/`get` spent their
  time in on HEALPix requests. The numpy implementation that was already there as the no-Rust fallback does the
  same work with two binary searches and a vectorised ring -> nested renumbering, ~1 us per point, and is now
  used unconditionally; `first_axis_vals` and `HEALPix_longitudes` still come from Rust. Indices are identical
  (checked against the Rust implementation on random rings and longitudes of HEALPix 32, 128 and 1024), as is
  the `None` returned for a value off the grid. `prepare` of the HEALPix-1024 Europe box (479,865 points) drops
  from 6.1 s to 0.49 s.

## Opt-in: one longitude leaf per latitude node for polygons and paths

`Polytope._merge_union_rows` (private class attribute, **default `False`**; set it on a `Polytope` instance before
slicing). Unions of non-orthogonal shapes (the triangles of a `Polygon`, the segments of a `Path`) left the leaf
(longitude) axis uncompressed, so every point was its own tree node (~1.3-1.4 KB/point, see `MEASUREMENTS.md`).
With the switch on the leaf axis stays compressed and the pieces' leaves under each latitude node are merged into
one sorted, de-duplicated float64 array (`datacube/tree_rows.py`).

- The flattened (latitude, longitude) point sequence is identical to the per-point tree, and so are `get`,
  `prepare` and `prune` results (`tests/test_polygon_rows.py`, regular / HEALPix nested
  128 / O1280, notched and seam-crossing polygons, missing fields).
- Merged leaves are flagged (`_keep_value_order`) so `get`/`prepare` keep their values ascending rather than
  reordering them by grid index as for box leaves, and put the results (fetched in index order) back into value
  order. On HEALPix nested grids this keeps the per-point (longitude) order instead of nested-index order.
- Leaf tags: a merged leaf carries the tag of its pieces. Where the pieces are tagged differently (several
  tagged polygons, several tagged `Point`s on a structured grid) the merged leaf gets per-point tags
  (`tag_ids` / `tag_sets`, `leaf.tags_of_point(i)`) and a point covered by several pieces the union of their
  tags, so such a union compresses too instead of falling back to one leaf per point. `leaf.tags` is the union
  over the leaf's points, as for any other node.
- Tree structure changes: `len(tree.leaves)` counts rows, not points; code counting points must sum
  `len(leaf.values)`.
- **Why it is off:** covjsonkit's legacy `walk_tree_step` (`from_polytope_step`, used for climate-dt and `ng`
  polygon and timeseries requests) slices each leaf's `result` assuming one point per leaf. With the switch on, the
  polytope-mars golden cases `cdt_polygon_sfc` and `cdt_polygon_single_param` change (fewer values per range);
  every other golden case, including `efas_polygon_fc` and `o1280_trajectory`, stays byte-identical. Turn it on
  once the polytope-mars block walker replaces the legacy walk for those requests.

## Merged: bulk spatial nodes and per-point tags

`feat/fix_tags_and_nearest_point` (`918580e3`: `1b3e37d5 684ed969 e7af5402 918580e3`) is merged whole. It
replaces the spatial layers of a request tree by one array-backed node per spatial sub-tree and derives the
gribjump index ranges from one sort of the whole field's grid indexes, which is what ends the HEALPix range
explosion (300,315 ranges -> 1,388 for the climate-dt Europe box; 7,864,320 -> 1 for a whole-world field). It
also gives every resolved point its own tags, fixes the nearest-point search to resolve each query on its own,
and makes a multi-value `Point` behave as a `Union` of single-value `Point`s.

### How a spatial sub-tree is retrieved: `bulk_grid_leaves`

Every spatial sub-tree of a tree being retrieved is one array-backed node (the section at the end of this
file retired the per-row alternative):

- a structured (hullslicer) tree's `latitude -> longitude` layers are folded, in `FDBDatacube.prepare`, into one
  `BulkGridTensorIndexNode` per path (`datacube/tree_fold.py`): `coordinates` (N, 2), `indexes` (N,) and one
  `result` array per field, the rows in tree order and, within a row, the longitude leaves in tree order, each
  leaf's points in grid-index order (ascending longitude for merged polygon rows). That is exactly the order
  the legacy CovJSON encoders read the tree in, so the output is unchanged: polytope-mars' golden corpus is
  byte-identical for all 28 cases, and `tests/test_bulk_fold.py` pins the rule itself against the rows of the
  sliced tree;
- an unstructured (quadtree) tree gets one `BulkMergedTensorIndexNode` per spatial sub-tree at slice time
  instead of one `MergedTensorIndexNode` per point;
- spatial axes cannot be selected: a spatial sub-tree is copied whole, and a field that fits the memory budget
  is fetched whole.

`options["bulk_grid_leaves"]` is accepted for configuration compatibility and ignored (`False` logs a warning).
Measurements: `MEASUREMENTS.md`.

### Tags

- `ConvexPolytope.tag` is carried through to every point a shape resolves to. A nearest-point query's tag ends
  up only on the point(s) actually nearest to it (`_retag_nearest_lons`), not on every candidate the slicer
  touched, and a point nearest to several queries carries all of their tags.
- `Point(axes, values, tag=[...])` tags each value separately, and a multi-value `Point` is resolved as a
  `Union` of single-value `Point`s -- it selects its points, not the cross product of their coordinates, which
  changes what a multi-value nearest `Point` returns.
- Per-point tags are stored as numpy: `tag_ids` (int32 per point, `None` when every point carries the same
  tags) into `tag_sets` (the distinct tag sets). `node.tags_of_point(i)` is the per-point accessor on array
  leaves and on both bulk node kinds; `node.tags` stays the union. There is no Python object per point.

### Nearest-point search

The swapped (longitude, latitude) query points are built as a copy, so the registered points are never mutated; `Polytope.retrieve` resets `datacube.nearest_search` per request and registers each
query point with the tag of the polytope it came from; the quadtree slicer resolves each nearest polytope with
its own points and `k` instead of taking them from the datacube, and its Python k-nearest fallback is
vectorised.

### Engine batching

`Engine.batches_polytopes` (True for `QuadTreeSlicer`) tells `Polytope.slice` that an engine resolves all
polytopes on its axes in one pass. Combinations whose non-batched polytopes are identical -- every `Point` of a
`Union` sharing the same `Select`s -- then build their tree prefix once and hand all of their lat/lon polytopes
to the engine together (`Polytope._group_combinations`). `Engine.reset()` is called once per `slice`.

## New API

- `TensorIndexTree.prune(select=None, latitude_axis="latitude")`, where `select` maps an axis to one value or
  to a sequence of values
- `TensorIndexTree.result_array()` / `MergedTensorIndexNode.result_array()`
- `TensorIndexTree.add_values(values)`
- `FDBDatacube.get(requests, context=None, select=None)`
- `FDBDatacube.prepare(requests, context=None, select=None)`: runs every step of `get` before
  the gribjump call (pruning, nearest-point selection, grid-index lookup, de-duplication of grid points,
  reordering of longitude leaf `values` by grid index and the fold into one node per spatial sub-tree) without
  fetching data or touching `result`. After `prepare`
  the tree holds the exact coordinates, in order, that `get` fills. Idempotent; `get` on a prepared tree or on
  `prepared.prune(select)` gives the same
  values/result order as `get` on the unprepared tree. Grid indices are recomputed by the later `get` rather than
  cached on the leaves, to keep a sliced tree at ~8 B/point.
- `FDBDatacube.get_iter(requests, context=None, select=None)`: builds the same gribjump call
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

### What a consumer reads from a bulk spatial node

The leaves of a prepared tree are `BulkGridTensorIndexNode` (structured grids) or
`BulkMergedTensorIndexNode` (point clouds), one per spatial sub-tree, and the whole spatial walk is:

- `node.coordinates`: float64 (N, 2) of `(latitude, longitude)` in output order;
- `node.point_count`: N;
- `node.indexes`: int64 (N,) canonical grid indexes of those points (what the ranges are derived from);
- `node.tags_of_point(i)` / `node.tags`: the tags of one point / of the node;
- `node.result`: after `get`, one array of N values per field of the call, in the order
  `itertools.product` gives the compressed axes above the node (float64, NaN where bitmap-missing; an object
  array of `None` for a field gribjump had no message for);
- `BulkGridTensorIndexNode` additionally exposes its rows: `lat_values`, `lon_values[i]` (a view on
  `coordinates`) and `row_slice(i)`;
- `get_iter` yields `(field_path, [(bulk_node, values), ...])`, one entry per spatial sub-tree, `values` a
  fresh float64 array in the node's point order, the second item `None` for a missing field;
- `tree.prune(select=...)` works on a tree holding bulk nodes and shares their arrays (`copy_shared`), so a
  per-field or per-group sub-tree costs nothing per point;
- `datacube.prototype_metrics` after `prepare`/`get`: `ranges_per_field`, `request_planning_s`,
  `uncompressed_requests`, `effective_range_arrays`, `gj_extract_call_s`, `iterator_and_assignment_s`.

## Follow-ups (not in this branch)

- **The request side costs ~0 per value now.** It used to cost ~90-210 B/value: `get_last_layer_before_leaf`
  collected every point's grid index as a Python `int` in a list per leaf and `sort_fdb_request_ranges` sorted
  `enumerate(...)` of those lists, building one tuple per point, which is what a one-field `get` peaked on
  (`MEASUREMENTS.md`: ~90 B/value on the EFAS Danube box, ~210 B/value on a HEALPix 1024 Europe box). The fold
  replaced both passes with numpy (24 B/point of node arrays, 66-75 B/point peak on every grid and shape
  measured) and the per-row code is gone (see the section at the end).
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
- **The fold's peak is 66-75 B/point**, against a steady state of 24 B/point. 32 B/point of that is the
  node's own arrays plus the field's values, 8 B/point is the buffer `gribjump.extract` allocates for the whole
  field before handing out the first result, and on HEALPix nested the ranges need an int64 permutation plus a
  sorted copy of the indexes (16 B/point transient). Writing the ranges from a sort that never materialises the
  permutation, or reading the field in pieces, would close the gap.

# One way to retrieve a spatial sub-tree

## Behaviour changes

- **A spatial sub-tree is always one array-backed node.** `FDBDatacube.get` / `get_iter` ask gribjump for one
  field of one bulk node per request and scatter each result into that node's point order; the per-row
  alternative -- one request per run of consecutive grid indices of a leaf, with the results written back into
  the leaves of the tree -- is gone. What goes with it: `datacube/fdb_assign.py` (`FieldRequests`,
  `ScatterPlan`), `FDBDatacube.get_2nd_last_values`, `get_last_layer_before_leaf`, `get_merged_2nd_last_values`,
  `nearest_lat_lon_search_merged`, `sort_fdb_request_ranges`, `remove_duplicates_in_request_ranges`, the
  `FDBDatacube.fold_into_bulk_grid` wrapper (callers use `tree_fold.fold_into_bulk_grid`), and
  `tree_values.finalise_result` / `restore_value_order`. `field_values_flat` moved into
  `datacube/backends/fdb.py`, next to its only caller. A leaf kind that cannot be folded raises
  `BadRequestError` instead of being fetched row by row.
- **`options["bulk_grid_leaves"]` is accepted and ignored** (`Datacube.bulk_grid_leaves` is `True`); `False`
  logs a warning saying so. The option stays so that a deployment's configuration keeps validating.
- **`prototype_metrics`** keeps `ranges_per_field`, `request_planning_s`, `uncompressed_requests`,
  `effective_range_arrays`, `gj_extract_call_s` and `iterator_and_assignment_s`.

## Why the per-row path went rather than staying as an alternative

It was unreachable for the only consumer that drives this branch (polytope-mars sets the fold for every
request) and it was the expensive side of every measurement in `MEASUREMENTS.md`: ~90-210 B/value of
request-side Python objects and, on HEALPix nested, one index range per 1.6 points. Keeping it would have
meant keeping 570 lines of code and tests for a path no caller takes.

## Verification

- `python -m pytest tests -m "not fdb and not internet and not non_stored_data" -q`: **385 passed,
  6 skipped** (was 464 passed, 6 skipped). The 79 tests that go were the ones whose oracle *was* the per-row
  path: `tests/test_flat_assign.py` and `tests/legacy_assign.py` (the per-range assignment it replaced), the
  latitude-band parametrisations of `tests/test_pruned_get.py` and `tests/test_polygon_rows.py` (bands are
  refused on a folded tree), and the fold-off arms of `tests/test_bulk_fold.py` and
  `tests/test_bulk_point_tags.py`.
- What replaces them: `tests/test_bulk_fold.py::test_folded_points_are_the_sliced_rows_in_order` states the
  fold's rule against the rows of the sliced tree (rows in tree order, each row's points in grid-index order,
  first occurrence of a duplicate index wins) for all five grid cases, and every value is checked to decode to
  the grid index of the coordinate it sits at (the fake encodes it). `tests/test_pruned_get.py` keeps the
  "pruned gets reproduce a full get" property with one sub-tree per field instead of per band.
- `performance/bulk_order.py` is gone: it compared the fold against the per-row path for the 28 golden cases.
  polytope-mars' corpus is the remaining end-to-end oracle for that order. `performance/bulk_memory.py` and
  `performance/tree_memory.py` measure the one path that is left (no `--legacy`, no `bulk` column).

# Pruning a tree to a set of values per axis

## Behaviour changes

- **`TensorIndexTree.prune(select=...)` takes a value or a sequence of values per axis.** A node on a selected
  axis keeps the listed values in its own order, so the compressed-axes expansion of `FDBDatacube.get` stays in
  tree order; a branch whose node holds none of them is dropped; a value that is nowhere in the tree raises
  `ValueError` naming the axis, as a single unknown value already did. One sub-tree can therefore carry several
  field groups, which is what polytope-mars plans a multi-group gribjump call from (its own multi-value
  `tree_units.prune_values`, a copy of this walk, is gone and with it three private names it imported from
  `tree_pruning`).
- **Latitude bands are gone**: `latitude_range` on `prune` / `get` / `get_iter` / `prepare`,
  `TensorIndexTree.latitude_point_counts` and `tree_pruning`'s band machinery (`_NO_BANDS`,
  `_subtree_points`). A spatial sub-tree is one array-backed node that is copied whole, so there is nothing to
  count or cut: a field fits the memory budget whole or is refused by the caller
  (polytope-mars `limits.max_points_per_field`). Selecting a spatial axis raises
  `Cannot select on spatial axis 'latitude'`.

## Verification

- `python -m pytest tests -m "not fdb and not internet and not non_stored_data" -q`: **386 passed, 6 skipped**.
  `tests/test_pruned_get.py::test_prune_selects_several_values_of_an_axis` pins the new form (the same records
  as a full get, the tree's value order whatever the caller's, a one-element sequence equal to the single-value
  form), and polytope-mars' golden corpus is byte-identical: every multi-group call it makes goes through this
  walk.
