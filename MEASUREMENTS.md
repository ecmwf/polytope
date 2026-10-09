# Request-tree memory and slice time

Global bounding box (`Box([-90, 0], [90, 360])`), one field, sliced with `Polytope.slice` against the in-memory fake
gribjump (`tests/fake_gribjump.py`). Reproduce with:

    python performance/tree_memory.py

Each grid runs in a fresh process (Python 3.11, numpy 2.4, Rust extension enabled, WSL2 x86_64). "Before" is
`develop` at `0970e3e2`, "after" is this branch.

| grid | points | | slice time | RSS growth during slice | tree after dropping slicer caches | `getsizeof` tree estimate | max RSS of process |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: |
| HEALPix nested 1024 | 12,582,912 | before | 134 s | 829 MB (69.1 B/pt) | 721 MB (60.1 B/pt) | 32.2 B/pt | 952 MB |
| | | after | 26 s | 108 MB (9.0 B/pt) | 108 MB (9.0 B/pt) | 8.2 B/pt | 233 MB |
| O1280 | 6,599,680 | before | 65 s | 579 MB (91.9 B/pt) | 448 MB (71.1 B/pt) | 32.2 B/pt | 704 MB |
| | | after | 14 s | 58 MB (9.2 B/pt) | 58 MB (9.2 B/pt) | 8.2 B/pt | 183 MB |

How to read the columns:

- **RSS growth during slice**: process RSS after the slice minus before it (after `gc.collect()`), including the
  hull slicer's caches.
- **Tree after dropping slicer caches**: the same after clearing `axis_values_between` and `remapped_vals`. Before
  this branch the RSS stays well above the 32 B/pt of the tree objects themselves. The memory freed from the caches
  and from the per-value tuple copies made while building leaves stays fragmented in the allocator and is not
  returned to the OS.
- **`getsizeof` tree estimate**: sum of `sys.getsizeof` over the nodes, their `__dict__`s and their `values`
  (including the float objects inside tuples).
- **Max RSS**: `ru_maxrss` of the measuring process, including about 125 MB of interpreter, numpy and polytope
  baseline.

Where the change comes from:

1. Longitude leaf values are a float64 array (8 B/pt) instead of a tuple of Python floats (8 B pointer + 24 B float).
2. A leaf's values are collected and sorted once. Before, each `add_value` copied and re-sorted the whole tuple,
   which was quadratic per latitude line and accounted for most of the slice time.
3. The slicer does not cache the per-line index lookups and per-value remaps on the leaf axis. Those caches held
   every point of the request as Python objects.

`tests/test_pruned_get.py::test_tree_memory_per_point_for_1m_point_slice` asserts the `getsizeof` estimate stays
below 16 B/pt for a 1M-point slice (regular 0.25° grid).

# Polygon trees: one leaf per point vs one leaf per latitude node

One field, sliced as polytope-mars builds polygon features (`Union(Polygon(...))`), against the fake gribjump.
Reproduce with:

    python performance/tree_memory.py --get healpix1024_europe_polygon efas_danube_polygon              # merged rows
    python performance/tree_memory.py --get --per-point healpix1024_europe_polygon efas_danube_polygon  # per point

"per point" is this branch with `Polytope._merge_union_rows = False` (the default, and what `develop` builds): the
longitude axis is not compressed for unions, so every point is a tree node. "rows" is
`_merge_union_rows = True`: one float64 leaf per latitude node. Both trees hold the same points in the same order.

- Europe: polytope-mars `tools/measure_memory.py` `EUROPE_POLYGON` (7 vertices, 35-71N, 15W-40E) on HEALPix
  nested 1024, cyclic longitude range [0, 360]. 321,936 points in 753 latitude nodes.
- Danube: a 15-vertex Danube-basin outline inside the EFAS Danube bounding box `[[50.25, 8.15], [42.08, 29.73]]`
  (`DANUBE_POLYGON` in `performance/tree_memory.py`) on the EFAS `local_regular` 2969x4529 grid; 400,655 of the
  box's 634,550 points.

| polygon | points | tree | tree nodes | slice | RSS growth (B/pt) | `getsizeof` (B/pt) | `prepare` | `get` | max RSS |
| --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Europe, H1024 | 321,936 | per point | 322,699 | 16.6 s | 411 MB (1,339) | 329 | 123 s | 129 s | 1,091 MB |
| | | rows | 1,516 | 2.2 s | 12.7 MB (41) | 9.4 | 5.2 s | 6.4 s | 218 MB |
| Danube, EFAS | 400,655 | per point | 401,155 | 20.5 s | 512 MB (1,339) | 328 | 43 s | 50 s | 1,355 MB |
| | | rows | 990 | 3.1 s | 14.1 MB (37) | 8.8 | 0.38 s | 0.36 s | 216 MB |

Columns as in the table above; `prepare` runs on a pruned copy of the tree, `get` on the tree itself, both with
one field. Max RSS includes ~125 MB of interpreter and imports.

- The per-point tree costs ~1.3 KB/point (a `TensorIndexTree`, its `__dict__`, a `SortedList` and a 1-element
  array per point). A global H1024 polygon (12.6M points) would need ~17 GB; with
  rows it is the ~9 B/pt of the global box above.
- `get`/`prepare` on the per-point tree are slow because `get_2nd_last_values` builds a list of
  `len(row)` x `len(row)` placeholders per latitude node (quadratic in the leaves per row) and handles every point
  as its own index range; on rows they cost the same as on a box.
- The RSS growth of the row tree (37-41 B/pt) is above its object size (9 B/pt): the per-piece leaf arrays are
  concatenated once per row at the end of the slice, and the freed pieces stay in the allocator.

# Regular / local_regular grid index lookup

`prepare`/`get` on a single field, fake gribjump, regular lat/lon global boxes and the EFAS `local_regular` Danube box
(`performance/tree_memory.py --get regular90_global_box regular180_global_box regular360_global_box efas_danube_box regular500_global_box`).
"Before" is this branch at the commit preceding `0b96fe7c`, where the mapper rebuilt the full longitude list for
every point and the cost grew quadratically; "after" is the vectorised O(log n) lookup. The two largest cases had
not completed after 15 minutes of the baseline run and are not quoted.

| scenario | points | before `prepare` / `get` | after `prepare` / `get` | slice | tree (B/pt) | max RSS |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| regular90_global_box | 64,800 | 3.8 s / 3.7 s | 0.02 s / 0.02 s | 0.09 s | 18.6 | 138.9 MB |
| regular180_global_box | 259,200 | 28 s / 28 s | 0.13 s / 0.11 s | 0.36 s | 12.7 | 177.8 MB |
| regular360_global_box | 1,036,800 | 217 s / 218 s | 0.5 s / 0.53 s | 1.49 s | 10.2 | 319.7 MB |
| efas_danube_box | 634,550 | not measured (quadratic) | 0.28 s / 0.28 s | 3.45 s | 11.0 | 240.9 MB |
| regular500_global_box | 2,000,000 | not measured (quadratic) | 1.11 s / 0.91 s | 3.07 s | 9.5 | 488.6 MB |

# What one `get` peaks at, per value

Peak RSS of a single `get`, sampled every 2 ms in a background thread, minus the RSS before the call (the sliced,
prepared tree is already there), over the values the call fetches (`n_points x n_fields`).  One field group, all
fields in one gribjump call (the `step` axis stays compressed).  Fake gribjump, each run in its own process:

    python performance/tree_memory.py --get --fields=12 healpix1024_europe_box            # flat, filling the tree
    python performance/tree_memory.py --get --fields=12 --iter healpix1024_europe_box     # flat, through get_iter

- **HEALPix nested 1024, Europe box** `[35, -15]` to `[71, 40]`: 357,409 points in 223,602 index ranges (1.6
  points per range).
- **EFAS `local_regular` 2969x4529, Danube box** `[42.08, 8.15]` to `[50.25, 29.73]`: 634,550 points in 490
  ranges (1,295 points per range).

"before" is the per-range assignment (`result.values[i]` per range, chunks of every leaf kept until the last field
arrived), measured while it was still there (`--legacy`, which went with the per-row path);
"after" is the flat one (`result.values_flat` once per field, scattered
into pre-allocated leaf results); "get_iter" consumes the same call field by field and drops each field.

| grid | fields | values | before | after | `get_iter` | before peak | after peak | `get_iter` peak |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| HEALPix 1024, Europe box | 1 | 357,409 | 236 B | 214 B | 239 B | 80.6 MB | 72.9 MB | 81.4 MB |
| | 4 | 1,429,636 | 120 B | 54 B | 53 B | 164.0 MB | 73.4 MB | 72.7 MB |
| | 12 | 4,288,908 | 108 B | 30 B | 26 B | 440.5 MB | 123.8 MB | 107.3 MB |
| EFAS, Danube box | 1 | 634,550 | 143 B | 147 B | 145 B | 86.6 MB | 89.1 MB | 87.4 MB |
| | 4 | 2,538,200 | 37 B | 36 B | 37 B | 88.3 MB | 87.5 MB | 88.3 MB |
| | 12 | 7,614,600 | 17 B | 17 B | 12 B | 121.5 MB | 123.6 MB | 88.2 MB |

HEALPix against the row-ordered grid, which is the number the polytope-mars unit planner needs to be grid
independent: **6.4x before, 1.8x after** at 12 fields (3.3x -> 1.5x at 4 fields).  `get` time on the HEALPix box
also drops (26.3 s -> 23.6 s at 12 fields; 1.2 s -> 0.32 s for 4 fields on the EFAS box).

Where the rest of the peak is, and what polytope-mars should size with:

- The **result side** is now 8 B/value (the leaf arrays) plus 8 B/value of gribjump buffer plus, on grids whose
  points a leaf does not cover in one ascending run, 4 B/value for the plan's positions.  Before, each index
  range cost a numpy view plus a list slot (~165 B measured), which on HEALPix is ~100 B per *value* and on a
  row-ordered grid ~0.1 B.
- The **request side** was what a small call peaked on while requests were planned row by row:
  `get_last_layer_before_leaf` collected
  every point's grid index as a Python `int` in a list and `sort_fdb_request_ranges` sorted `enumerate(...)` of
  those lists.  Measured (`request_bytes_per_value x fields`): **~210 B per point on HEALPix nested, ~88 B per
  point on EFAS**, independent of the number of fields.  Both passes are gone with the per-row path;
  the fold's own cost is in the section below.
- So the Python side of one call is about `n_points x 220 B + n_values x 24 B` on every grid measured (that bound
  holds for all six rows above, with room to spare on the row-ordered grid).  The 24 B/value term is the
  grid-independent constant; the per-point term is paid once per call however many fields it has, so it is
  ~20 B/value for a 12-field unit and 220 B/value for a single field.
- `get_iter` does not keep the values: after a 12-field HEALPix call the process is at 187 MB rather than 259 MB,
  and its peak is the lowest of the three (one field's arrays at a time instead of all twelve).

The gribjump buffer itself (`extract_mb`: the fake builds every field's values before handing out the first
result, as `GribJump::extract` does) shows up as 23-26 MB for a 12-field call, i.e. ~6 B/value
against the 8 B/value of doubles it allocates: the rest is absorbed into memory the request bookkeeping had just
freed.  For 1 and 4 fields it is entirely absorbed and measures 0.1 MB.

The flat path was also checked against the per-range one at this scale, not only in the unit tests: the same
HEALPix 1024 Europe box with 4 compressed fields (753 leaves, 1,429,636 values) gives identical leaf values and
`result_array()` under both implementations.

# One bulk spatial node per field: whole-field ranges instead of per-row ranges

One field, sliced as polytope-mars builds its features (`_merge_union_rows = True`), then `prepare` and `get`
against polytope-mars' fake gribjump, with `bulk_grid_leaves` off and on (the `off` rows were measured while
the option could still be turned off; `spatial_node_memory.py` now measures the one path that is left).  Each row is a fresh subprocess; peak
is `resource.getrusage(RUSAGE_SELF).ru_maxrss` of that process.  Reproduce the `on` rows with:

    python performance/spatial_node_memory.py            # every shape
    python performance/spatial_node_memory.py SHAPE ...  # see performance/spatial_node_memory.py SHAPES

| shape | bulk | points | slice s | tree MB | tree B/pt | prepare s | get s | growth B/pt | peak growth B/pt | peak MB | ranges/field |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| EFAS Danube box | off | 634,550 | 3.3 | 6.6 | 8.5 | 0.29 | 0.29 | 81.8 | 172.7 | 270.9 | 490 |
| | **on** | | 3.4 | 6.6 | 8.5 | **0.05** | 0.01 | **55.5** | **65.7** | **206.2** | 490 |
| HEALPix-1024 Europe box | off | 479,865 | 1.2 | 6.8 | 9.0 | 1.08 | 1.10 | 123.2 | 288.4 | 299.4 | 300,315 |
| | **on** | | 1.2 | 6.7 | 9.0 | **0.46** | 0.01 | **72.6** | **70.5** | **199.6** | **1,388** |
| HEALPix-1024 Europe polygon | off | 321,936 | 2.1 | 13.1 | 9.4 | 0.82 | 0.90 | 187.9 | 257.4 | 252.7 | 201,454 |
| | **on** | | 1.8 | 13.1 | 9.4 | **0.39** | 0.01 | **68.4** | **66.6** | **194.4** | **1,116** |
| EFAS Europe polygon | off | 6,426,480 | 34.8 | 119.4 | 8.2 | 5.44 | 5.61 | 9.4 | 173.1 | 1,340.4 | 2,160 |
| | **on** | | 34.8 | 120.5 | 8.2 | **0.37** | 0.12 | 23.9 | **65.7** | **683.4** | 2,160 |
| HEALPix-1024 whole world box | off | 12,582,912 | 24.8 | 107.1 | 8.2 | 37.2 | 36.9 | 24.6 | 246.5 | 3,225.3 | 7,864,320 |
| | **on** | | 25.5 | 106.9 | 8.2 | **7.1** | 0.40 | 35.0 | **74.9** | **1,166.4** | **1** |
| EFAS whole domain box | off | 13,454,100 | 67.7 | 111.6 | 8.1 | 17.5 | 17.4 | 17.6 | 177.5 | 2,548.6 | 2,970 |
| | **on** | | 67.5 | 111.7 | 8.1 | **0.82** | 0.29 | 33.5 | **65.9** | **1,116.5** | **2** |
| O1280 whole world box | off | 6,599,680 | 12.9 | 57.2 | 8.2 | 7.7 | 7.2 | 31.3 | 204.1 | 1,503.1 | 2,560 |
| | **on** | | 13.2 | 57.3 | 8.2 | **2.5** | 0.15 | 37.8 | **74.6** | **687.6** | **1** |

How to read the columns:

- **tree MB / tree B/pt**: RSS growth during the slice, and the `getsizeof` estimate of the tree.  The fold runs in
  `prepare`, so the sliced tree is the same with it off and on.
- **prepare s**: `prepare` on the sliced tree, which is where the ranges are planned (`get s` is then only the
  gribjump call and the assignment; with the fold off `get` re-plans the ranges, hence the two similar numbers).
- **growth B/pt**: RSS after `prepare` + `get` minus RSS after the slice, per point.
- **peak growth B/pt**: the process peak minus RSS after the slice, per point -- what a field costs on top of
  its tree.
- **ranges/field**: index ranges one field's gribjump request asks for (`prototype_metrics["ranges_per_field"]`,
  summed over the spatial sub-trees of the call).

What it says:

1. **Whole-field ranges end the HEALPix range explosion**: 300,315 -> 1,388 on the Europe box (216x), 201,454 ->
   1,116 on the Europe polygon (180x), 7,864,320 -> **1** on the whole world.  A box that covers a whole
   row-ordered grid is one range (O1280, EFAS) and never more than one per discontinuity.  The ranges are exact:
   they are the gaps in the field's sorted indexes, so nothing is over-fetched.
2. **`prepare` is 2-20x faster** and does not grow with the number of rows: 0.39 s for the HEALPix Europe
   polygon (5.2 s before the HEALPix mapper was vectorised, 0.82 s after), 0.82 s for a 13.5M-point EFAS field
   against 17.5 s, 7.1 s for a 12.6M-point HEALPix field against 37.2 s.
3. **The peak is flat across grids and shapes**: 66-75 B/point with the fold, against 173-288 B/point without,
   and it does not depend on how the grid numbers its points.  It is made of the node's own arrays
   (coordinates 16 + indexes 8 B/pt), the field's values (8 B/pt), the gribjump buffer the extract call
   allocates for the whole field before handing out the first result (8 B/pt), and -- only on grids whose points
   a request does not cover in ascending index order, i.e. HEALPix nested -- the sort the ranges come from
   (int64 permutation plus sorted copy, 16 B/pt transient, 4 B/pt kept as int32).  The remainder is what the
   allocator keeps after the transients are freed.
4. The steady state is 24-56 B/point on every shape; the peak lands at 66-75 B/point.  32 B/point of that is
   the node and the values, 8 B/point is gribjump's own buffer, and the rest is the sort and allocator
   retention; see the breakdown above.

# Many nearest points: one resolution per request instead of one search per point

A timeseries request with N nearest `Point`s, sliced and prepared against polytope-mars' fake gribjump
(`polytope_mars.testing`), with pseudo-random points over the globe.  Reproduce with:

    python performance/nearest_points.py --path new --path old --n 1000 10000 100000

Each row is a fresh subprocess (Python 3.11, numpy 2.4, Rust extension enabled, WSL2 x86_64, 32 cores);
"peak MB" is `ru_maxrss` of that process and includes ~170 MB of interpreter, numpy, polytope and
polytope-mars baseline.  `old` is this branch with the batching switched off, which leaves the path it
replaces: one tree prefix descent per point in `slice`, then `FDBDatacube.nearest_lat_lon_search` rebuilding
and sorting all 4N candidates of the request once per point in `prepare`.

| grid | path | requested | points | slice s | prepare s | total s | peak MB |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| O1280 | old | 1,000 | 1,000 | 0.71 | 2.06 | 2.77 | 171 |
| | **new** | | 1,000 | **0.24** | **0.00** | **0.24** | 171 |
| O1280 | old | 10,000 | 9,974 | 7.60 | 365 | 373 | 221 |
| | **new** | | 9,974 | **0.55** | **0.00** | **0.55** | 178 |
| O1280 | old | 100,000 | 98,010 | 81 | ~10 h (extrapolated) | | 635 |
| | **new** | | 98,010 | **1.76** | **0.02** | **1.78** | **324** |
| HEALPix nested 1024 | old | 1,000 | 1,000 | 1.43 | 2.54 | 3.96 | 171 |
| | **new** | | 1,000 | **0.69** | **0.00** | **0.69** | 171 |
| HEALPix nested 1024 | old | 10,000 | 9,985 | 14.73 | 383 | 398 | 224 |
| | **new** | | 9,985 | **2.47** | **0.00** | **2.47** | 177 |
| HEALPix nested 1024 | old | 100,000 | 98,880 | 152 | ~10 h (extrapolated) | | 655 |
| | **new** | | 98,880 | **3.93** | **0.02** | **3.95** | **323** |

Both paths return the same points, in the same order: the `points` column is one figure per request, and
`tests/test_nearest_grid.py` compares the two paths point by point.  The 100,000-point `old` rows are the
slice alone, measured without `prepare` (which would take about 10 hours); their point count is the one the
batched path returns.  The old slice of 100,000 points on HEALPix nested 1024 also leaves the interpreter
segfaulting on exit, while freeing the 196,922 nodes it built (193,834 on O1280) -- the batched path builds
one node.

What it says:

1. **The search was O(N^2)** and is the whole of the old `prepare`: 2.1 s, 8.6 s, 44.1 s, 365 s for 1,000,
   2,000, 4,000 and 10,000 points on O1280 (2.5 s, 9.7 s, 48.0 s, 383 s on HEALPix nested 1024).  Fitting
   `3.7e-6 s * N^2` to the 10,000-point figure puts 100,000 points at about 10 hours, and the growth above
   4,000 points is slightly worse than quadratic.  The production consequence is the result store's 300 s
   writer-inactivity timeout: a point feature emits the collection header and then nothing until the
   extraction starts, so a request whose `prepare` takes longer than that is killed -- about 8,500 scattered
   points today.
2. **`prepare` has nothing left to do**: the points are resolved into their bulk node while slicing, so
   `prepare` only plans the gribjump ranges (0.02 s for 98,010 points).
3. **The slice is no longer per point either.** The N points of one `Union` share a tree prefix, so it is
   built once instead of 100,000 times: 1.76 s against 81 s at 100,000 points on O1280 (3.93 s against 152 s
   on HEALPix nested 1024), and one tree node against 193,834.  Peak memory follows: 324 MB against 635 MB,
   i.e. 1.6 kB per requested point against 5.1 kB.  What is left is dominated by the request's own Python
   objects (4 `ConvexPolytope`s per point across the three `request.polytopes()` calls a retrieve makes,
   0.4 s at 100,000 points) rather than by the grid.
4. **The resolution itself costs 1.1 s for 100,000 points on O1280** (3.0 s on HEALPix nested 1024) --
   1.05 s of the 1.67 s slice, measured by timing `nearest_grid.resolve` alone.  At 1,000 points it is
   0.22 s on O1280 and 0.68 s on HEALPix, nearly all of it building the grid rows the queries touch: the
   search needs each row's longitudes to bracket a query in it, and 1,000 scattered points touch 1,343 of
   the 2,560 O1280 rows and 1,539 of the 4,095 HEALPix rings (2.5M longitudes).  That cost is bounded by the
   grid, not by N, which is why 100 times more points cost 2-4 times more rather than 100 times: the whole
   grid is 6.6M (O1280) and 12.6M (HEALPix) longitudes.
5. **Where the new path crosses 1 s**: about 35,000 points on O1280 (0.55 s at 10,000, 0.93 s at 30,000,
   1.24 s at 50,000) and about 1,600 points on HEALPix nested 1024 (0.94 s at 1,500, 1.19 s at 2,000), the
   HEALPix figure being the ring-building above.
6. **Requested points that snap to the same grid point are returned once**, on both paths: 26 of 10,000 and
   1,990 of 100,000 on O1280, 15 and 1,120 on HEALPix nested 1024 for these random points.  A request gets
   fewer coverages than it asked for with nothing saying which ones were merged; the resolved node now
   carries `point_of_query` so that a consumer can report one coverage per requested point.
