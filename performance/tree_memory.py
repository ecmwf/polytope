"""Measure request-tree memory per point, slice time and prepare/get time.

Uses an in-memory fake gribjump (``tests/fake_gribjump.py``) so no FDB is needed.  Each scenario is measured in a
fresh subprocess so the RSS numbers do not interfere with each other.

    python performance/tree_memory.py                       # the global boxes (slice only)
    python performance/tree_memory.py SCENARIO [...]        # named scenarios, see SCENARIOS
    python performance/tree_memory.py --get SCENARIO [...]  # also time prepare() and get()
    python performance/tree_memory.py --per-point SCENARIO  # polygons with one leaf node per point
    python performance/tree_memory.py healpix_nested 1024   # global box on one grid (as before)
"""

import gc
import json
import os
import resource
import subprocess
import sys
import time
from importlib.util import module_from_spec, spec_from_file_location

EFAS_GRID = {
    "type": "local_regular",
    "resolution": [2969, 4529],
    "local": [22.758333333333333, 72.24166666666666, -25.241666666666667, 50.24166666666667],
    "axis_reversed": {"latitude": True, "longitude": False},
}
GLOBAL_BOX = ("box", [-90, 0], [90, 360])
# polytope-mars tools/measure_memory.py EUROPE_POLYGON, as (lat, lon), without the repeated closing vertex
EUROPE_POLYGON = [[35, -10], [35, 30], [45, 40], [60, 40], [71, 30], [71, -10], [60, -15]]
# A Danube-basin outline inside the EFAS Danube bounding box [[50.25, 8.15], [42.08, 29.73]] (15 vertices)
DANUBE_POLYGON = [
    [48.0, 8.15],
    [49.5, 9.5],
    [50.25, 12.5],
    [49.8, 16.0],
    [50.0, 19.5],
    [49.0, 22.5],
    [48.5, 26.0],
    [46.0, 29.73],
    [44.0, 29.0],
    [42.08, 24.0],
    [42.5, 20.0],
    [43.5, 16.5],
    [45.5, 13.5],
    [46.5, 10.0],
    [47.3, 8.5],
]

# name -> (mapper options, longitude cyclic range, shape)
SCENARIOS = {
    "healpix1024_global_box": ({"type": "healpix_nested", "resolution": 1024}, [0, 360], GLOBAL_BOX),
    "o1280_global_box": ({"type": "octahedral", "resolution": 1280}, [0, 360], GLOBAL_BOX),
    "healpix1024_europe_polygon": (
        {"type": "healpix_nested", "resolution": 1024},
        [0, 360],
        ("polygon", EUROPE_POLYGON),
    ),
    "efas_danube_polygon": (EFAS_GRID, [-180, 180], ("polygon", DANUBE_POLYGON)),
    "efas_danube_box": (EFAS_GRID, [-180, 180], ("box", [42.08, 8.15], [50.25, 29.73])),
    # global regular boxes: 8 * resolution**2 points
    "regular90_global_box": ({"type": "regular", "resolution": 90}, [0, 360], GLOBAL_BOX),
    "regular180_global_box": ({"type": "regular", "resolution": 180}, [0, 360], GLOBAL_BOX),
    "regular360_global_box": ({"type": "regular", "resolution": 360}, [0, 360], GLOBAL_BOX),
    "regular500_global_box": ({"type": "regular", "resolution": 500}, [0, 360], GLOBAL_BOX),
}
DEFAULT_SCENARIOS = ["healpix1024_global_box", "o1280_global_box"]


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


def _shape(spec):
    from polytope_feature.shapes import Box, Polygon, Union

    if spec[0] == "box":
        return Box(["latitude", "longitude"], spec[1], spec[2])
    # as polytope-mars builds polygon features
    return Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], spec[1]))


def _tree_stats(tree):
    n_points = n_nodes = n_lat = deep_bytes = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        n_nodes += 1
        if node.axis.name == "latitude":
            n_lat += 1
        deep_bytes += sys.getsizeof(node) + sys.getsizeof(node.__dict__) + _values_bytes(node.values)
        if len(node.children) == 0:
            n_points += len(node.values)
        else:
            stack.extend(node.children)
    return n_points, n_nodes, n_lat, deep_bytes


def measure(mapper, cyclic_range, shape_spec, per_point=False, with_get=False):
    import psutil

    GribJump = _load_fake_gribjump().GribJump

    from polytope_feature.polytope import Polytope, Request
    from polytope_feature.shapes import Select

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
                "transformations": [dict(name="mapper", axes=["latitude", "longitude"], **mapper)],
            },
            {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": cyclic_range}]},
        ],
        "compressed_axes_config": ["longitude", "latitude", "levtype", "step", "date", "domain", "expver", "param"]
        + ["class", "stream", "type"],
        "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
    }
    gj = GribJump(axes)
    api = Polytope(datacube=gj, options=options)
    if hasattr(api, "_merge_union_rows"):
        api._merge_union_rows = not per_point
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
        _shape(shape_spec),
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
    n_points, n_nodes, n_lat, deep_bytes = _tree_stats(tree)
    out = {
        "points": n_points,
        "lat_nodes": n_lat,
        "tree_nodes": n_nodes,
        "slice_s": round(t1 - t0, 2),
        "tree_rss_mb": round((rss1 - rss0) / 2**20, 1),
        "bytes_per_point": round((rss1 - rss0) / n_points, 1),
        "tree_only_rss_mb": round((rss2 - rss0) / 2**20, 1),
        "tree_only_bytes_per_point": round((rss2 - rss0) / n_points, 1),
        "getsizeof_bytes_per_point": round(deep_bytes / n_points, 1),
        "rss_before_slice_mb": round(rss0 / 2**20, 1),
        "rss_after_slice_mb": round(proc.memory_info().rss / 2**20, 1),
    }
    if with_get:
        prepared = tree.prune() if hasattr(tree, "prune") else None
        if prepared is not None and hasattr(datacube, "prepare"):
            t0 = time.perf_counter()
            datacube.prepare(prepared)
            out["prepare_s"] = round(time.perf_counter() - t0, 2)
            del prepared
        t0 = time.perf_counter()
        datacube.get(tree)
        out["get_s"] = round(time.perf_counter() - t0, 2)
        gc.collect()
        out["rss_after_get_mb"] = round(proc.memory_info().rss / 2**20, 1)
    # ru_maxrss is in KiB on Linux
    out["max_rss_mb"] = round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 1)
    return out


def main(argv):
    flags = {a for a in argv if a.startswith("--")}
    args = [a for a in argv if not a.startswith("--")]
    with_get = "--get" in flags
    per_point = "--per-point" in flags
    if "--child" in flags:
        name = args[0]
        if name in SCENARIOS:
            mapper, cyclic_range, shape = SCENARIOS[name]
        else:
            grid_type, resolution = name.split(":")
            mapper, cyclic_range, shape = {"type": grid_type, "resolution": int(resolution)}, [0, 360], GLOBAL_BOX
        print(json.dumps(measure(mapper, cyclic_range, shape, per_point, with_get)))
        return
    if len(args) == 2 and args[1].isdigit():
        names = [f"{args[0]}:{args[1]}"]
    else:
        names = args or DEFAULT_SCENARIOS
    for name in names:
        if name not in SCENARIOS and ":" not in name:
            sys.exit(f"unknown scenario {name!r}; choose from {', '.join(SCENARIOS)}")
        cmd = [sys.executable, __file__, "--child", name] + sorted(flags)
        out = subprocess.run(cmd, capture_output=True, text=True, check=True)
        result = json.loads(out.stdout.strip().splitlines()[-1])
        print(json.dumps({"scenario": name, "per_point": per_point, **result}))


if __name__ == "__main__":
    main(sys.argv[1:])
