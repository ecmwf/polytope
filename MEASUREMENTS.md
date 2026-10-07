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
