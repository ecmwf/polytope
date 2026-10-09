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
  the last field had arrived. It now takes `result.values_flat` once per field and scatters it into the leaves by
  a plan built per spatial sub-tree (`datacube/fdb_assign.py`), and a leaf's result for the whole call is
  pre-allocated (`n_points x n_fields`, float64, NaN-filled) and filled field by field. Values, point order,
  the object/`None` result of a missing field and the value order of merged polygon rows are unchanged
  (`tests/test_flat_assign.py` compares every scenario against the per-range implementation, kept in
  `tests/legacy_assign.py`). On grids whose points a bounding box covers in long runs (regular, octahedral,
  local_regular) nothing changes measurably; on HEALPix nested grids, where a box breaks into roughly one range
  per 1.6 points, the peak of a 12-field `get` falls from ~370 to ~40 B/value. See `MEASUREMENTS.md`.
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
  `prepare`, `prune` and `latitude_point_counts` results (`tests/test_polygon_rows.py`, regular / HEALPix nested
  128 / O1280, notched and seam-crossing polygons, missing fields, bands).
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

### Opt-in: `bulk_grid_leaves`

Config option (`options["bulk_grid_leaves"]`, **default `False`**), carried by `Datacube.bulk_grid_leaves`. With
it on:

- a structured (hullslicer) tree's `latitude -> longitude` layers are folded, in `FDBDatacube.prepare`, into one
  `BulkGridTensorIndexNode` per path (`datacube/tree_fold.py`): `coordinates` (N, 2), `indexes` (N,) and one
  `result` array per field, the rows in tree order and, within a row, the longitude leaves in tree order, each
  leaf's points in the grid-index order `prepare` already gives them (ascending longitude for merged polygon
  rows). That is exactly the order the legacy CovJSON encoders read the tree in, so the output is unchanged:
  `performance/bulk_order.py` asserts the ordered `(lat, lon)` list and the per-field values are identical with
  the fold off and on for all 28 polytope-mars golden cases;
- an unstructured (quadtree) tree gets one `BulkMergedTensorIndexNode` per spatial sub-tree at slice time
  instead of one `MergedTensorIndexNode` per point;
- `latitude_point_counts()`, `prune(latitude_range=)` and `get(latitude_range=)` raise: a field that fits the
  memory budget is fetched whole. They are unchanged with the option off.

With the option off the trees are exactly what they were, which is why the polytope-mars golden corpus is
byte-identical and its 309 tests pass unchanged. Measurements: `MEASUREMENTS.md`.

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

### What a consumer reads from a bulk spatial node

With `bulk_grid_leaves` on, the leaves of a prepared tree are `BulkGridTensorIndexNode` (structured grids) or
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
  per-field or per-group sub-tree costs nothing per point; `latitude_range` is refused (see above);
- `datacube.prototype_metrics` after `prepare`/`get`: `ranges_per_field`, `request_planning_s`,
  `uncompressed_requests`, `effective_range_arrays`, `gj_extract_call_s`, `iterator_and_assignment_s`.

## Follow-ups (not in this branch)

- **The request side still costs ~90-210 B/value with `bulk_grid_leaves` off.** `get_last_layer_before_leaf`
  collects every point's grid index as a Python `int` in a list per leaf, and `sort_fdb_request_ranges` then
  sorts `enumerate(...)` of those lists, which builds one tuple per point. That is what a one-field `get` peaks
  on (`MEASUREMENTS.md`): ~90 B/value on the EFAS Danube box, ~210 B/value on a HEALPix 1024 Europe box. The
  fold replaces both passes with numpy (24 B/point of node arrays, 66-75 B/point peak on every grid and shape
  measured); the per-row path is what remains once polytope-mars turns the fold on.
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
- **Latitude bands are still there with `bulk_grid_leaves` off.** `latitude_range` / `latitude_point_counts` and
  the banded `prepare` can be deleted once no caller fetches a field in latitude bands.
