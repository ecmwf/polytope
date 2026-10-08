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
3. The slicer no longer caches the per-line index lookups and per-value remaps on the leaf axis. Those caches held
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
  nested 1024, cyclic longitude range [0, 360]. Same point and latitude-node count as Phase 0 (321,936 / 753).
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
  array per point), matching Phase 0's 1,385 B/pt. A global H1024 polygon (12.6M points) would need ~17 GB; with
  rows it is the ~9 B/pt of the global box above.
- `get`/`prepare` on the per-point tree are slow because `get_2nd_last_values` builds a list of
  `len(row)` x `len(row)` placeholders per latitude node (quadratic in the leaves per row) and handles every point
  as its own index range; on rows they cost the same as on a box.
- The RSS growth of the row tree (37-41 B/pt) is above its object size (9 B/pt): the per-piece leaf arrays are
  concatenated once per row at the end of the slice, and the freed pieces stay in the allocator.

# Regular / local_regular grid index lookup

`prepare`/`get` on a single field, fake gribjump, regular lat/lon global boxes and the EFAS `local_regular` Danube box
(`performance/tree_memory.py --get regular90_global_box regular180_global_box regular360_global_box efas_danube_box regular500_global_box`).
"Before" is Phase 1b's measurement on this branch before commit `0b96fe7c` (the mapper rebuilt the full longitude list for
every point, so cost grew quadratically); "after" is the vectorised O(log n) lookup. The baseline run for the two largest
cases was stopped after 15 minutes without completing.

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
    python performance/tree_memory.py --get --fields=12 --legacy healpix1024_europe_box   # per-range assignment

- **HEALPix nested 1024, Europe box** `[35, -15]` to `[71, 40]`: 357,409 points in 223,602 index ranges (1.6
  points per range).
- **EFAS `local_regular` 2969x4529, Danube box** `[42.08, 8.15]` to `[50.25, 29.73]`: 634,550 points in 490
  ranges (1,295 points per range).

"before" is the per-range assignment (`result.values[i]` per range, chunks of every leaf kept until the last field
arrived) kept in `tests/legacy_assign.py`; "after" is the flat one (`result.values_flat` once per field, scattered
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
- The **request side** is unchanged and is now what a small call peaks on: `get_last_layer_before_leaf` collects
  every point's grid index as a Python `int` in a list and `sort_fdb_request_ranges` sorts `enumerate(...)` of
  those lists.  Measured (`request_bytes_per_value x fields`): **~210 B per point on HEALPix nested, ~88 B per
  point on EFAS**, independent of the number of fields.  See the follow-up in `CHANGES.md`.
- So the Python side of one call is about `n_points x 220 B + n_values x 24 B` on every grid measured (that bound
  holds for all six rows above, with room to spare on the row-ordered grid).  The 24 B/value term is the
  grid-independent constant; the per-point term is paid once per call however many fields it has, so it is
  ~20 B/value for a 12-field unit and 220 B/value for a single field.
- `get_iter` does not keep the values: after a 12-field HEALPix call the process is at 187 MB rather than 259 MB,
  and its peak is the lowest of the three (one field's arrays at a time instead of all twelve).

The gribjump buffer itself (`extract_mb`: the fake builds every field's values before handing out the first
result, as `GribJump::extract` does -- see `CHANGES.md`) shows up as 23-26 MB for a 12-field call, i.e. ~6 B/value
against the 8 B/value of doubles it allocates: the rest is absorbed into memory the request bookkeeping had just
freed.  For 1 and 4 fields it is entirely absorbed and measures 0.1 MB.

The flat path was also checked against the per-range one at this scale, not only in the unit tests: the same
HEALPix 1024 Europe box with 4 compressed fields (753 leaves, 1,429,636 values) gives identical leaf values and
`result_array()` under both implementations.
