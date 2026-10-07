"""Measure request-tree memory per point and slice time for a global bounding box.

Uses an in-memory fake gribjump (``tests/fake_gribjump.py``) so no FDB is needed.  Each grid is measured in a
fresh subprocess so the RSS numbers do not interfere with each other.

    python performance/tree_memory.py                 # all grids
    python performance/tree_memory.py healpix_nested 1024
"""

import gc
import json
import os
import resource
import subprocess
import sys
import time
from importlib.util import module_from_spec, spec_from_file_location

GRIDS = [("healpix_nested", 1024), ("octahedral", 1280)]


def _load_fake_gribjump():
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "fake_gribjump.py")
    spec = spec_from_file_location("fake_gribjump", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load fake gribjump from {path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _values_bytes(values):
    """Deep size of a node's ``values``: container plus element objects (numpy arrays own their buffer)."""
    size = sys.getsizeof(values)
    if isinstance(values, tuple):
        size += sum(sys.getsizeof(v) for v in values)
    return size


def measure(grid_type, resolution):
    import psutil

    GribJump = _load_fake_gribjump().GribJump

    from polytope_feature.polytope import Polytope, Request
    from polytope_feature.shapes import Box, Select

    axes = {
        "class": ["od"],
        "date": ["20240101"],
        "time": ["0000"],
        "domain": ["g"],
        "expver": ["0001"],
        "levtype": ["sfc"],
        "param": ["167"],
        "step": ["0"],
        "stream": ["oper"],
        "type": ["fc"],
    }
    options = {
        "axis_config": [
            {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
            {
                "axis_name": "date",
                "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
            },
            {
                "axis_name": "values",
                "transformations": [
                    {
                        "name": "mapper",
                        "type": grid_type,
                        "resolution": resolution,
                        "axes": ["latitude", "longitude"],
                    }
                ],
            },
            {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
        ],
        "compressed_axes_config": ["longitude", "latitude", "levtype", "step", "date", "domain", "expver", "param"]
        + ["class", "stream", "type"],
        "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
    }
    api = Polytope(datacube=GribJump(axes), options=options)
    request = Request(
        Select("step", [0]),
        Select("levtype", ["sfc"]),
        Select("date", ["20240101T000000"]),
        Select("domain", ["g"]),
        Select("expver", ["0001"]),
        Select("param", ["167"]),
        Select("class", ["od"]),
        Select("stream", ["oper"]),
        Select("type", ["fc"]),
        Box(["latitude", "longitude"], [-90, 0], [90, 360]),
    )
    datacube = api.datacube
    if datacube is None:
        raise RuntimeError("fake gribjump was not recognised as an FDB datacube")
    datacube.check_branching_axes(request)
    proc = psutil.Process()
    gc.collect()
    rss0 = proc.memory_info().rss
    t0 = time.perf_counter()
    tree = api.slice(datacube, request.polytopes())
    t1 = time.perf_counter()
    gc.collect()
    rss1 = proc.memory_info().rss
    # Drop the slicer's caches so the remaining RSS growth is the tree itself.
    for engine in api.engines.values():
        engine.axis_values_between.clear()
        engine.remapped_vals.clear()
    gc.collect()
    rss2 = proc.memory_info().rss
    n_points = 0
    n_nodes = 0
    deep_bytes = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        n_nodes += 1
        deep_bytes += sys.getsizeof(node) + sys.getsizeof(node.__dict__) + _values_bytes(node.values)
        if len(node.children) == 0:
            n_points += len(node.values)
        else:
            stack.extend(node.children)
    return {
        "grid": f"{grid_type} {resolution}",
        "points": n_points,
        "slice_s": round(t1 - t0, 1),
        "tree_rss_mb": round((rss1 - rss0) / 2**20, 1),
        "bytes_per_point": round((rss1 - rss0) / n_points, 1),
        "tree_only_rss_mb": round((rss2 - rss0) / 2**20, 1),
        "tree_only_bytes_per_point": round((rss2 - rss0) / n_points, 1),
        "tree_nodes": n_nodes,
        "getsizeof_bytes_per_point": round(deep_bytes / n_points, 1),
        "rss_before_slice_mb": round(rss0 / 2**20, 1),
        "rss_after_slice_mb": round(proc.memory_info().rss / 2**20, 1),
        # ru_maxrss is in KiB on Linux
        "max_rss_mb": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1),
    }


def main():
    if len(sys.argv) == 3:
        if not sys.argv[2].isdigit():
            sys.exit(f"usage: {sys.argv[0]} [GRID_TYPE RESOLUTION]")
        print(json.dumps(measure(sys.argv[1], int(sys.argv[2]))))
        return
    for grid_type, resolution in GRIDS:
        out = subprocess.run(
            [sys.executable, __file__, grid_type, str(resolution)], capture_output=True, text=True, check=True
        )
        print(out.stdout.strip().splitlines()[-1])


if __name__ == "__main__":
    main()
