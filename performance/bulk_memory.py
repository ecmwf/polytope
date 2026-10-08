"""Measure one field's slice, ``prepare`` and ``get`` with the spatial layers folded into a bulk node or not.

Drives the real ``FDBDatacube`` against polytope-mars' fake gribjump (``polytope_mars.testing``), so the grids,
mapper options and MARS paths are the ones the deployments use.  Every (shape, bulk) pair runs in a fresh
subprocess; peak memory is ``resource.getrusage(RUSAGE_SELF).ru_maxrss`` of that process.

    python performance/bulk_memory.py                     # every shape, fold off and on
    python performance/bulk_memory.py SHAPE [...]          # named shapes, see SHAPES
    python performance/bulk_memory.py --json              # one JSON object per run instead of the table

Columns: points, slice time, tree size after the slice (RSS growth and the ``getsizeof`` estimate),
``prepare`` time, the request planning time inside it, the growth and peak growth of ``prepare`` + ``get`` over
the sliced tree, the process peak, and the index ranges the call asks gribjump for per field.
"""

import argparse
import gc
import json
import os
import resource
import subprocess
import sys
import time

MiB = 1024 * 1024

#: polytope-mars tools/measure_memory.py EUROPE_POLYGON (lat, lon)
EUROPE_POLYGON = [[35, -10], [35, 30], [45, 40], [60, 40], [71, 30], [71, -10], [60, -15], [35, -10]]

#: the MARS keys of one field per grid, as polytope-mars' fake axis tables declare them
REQUESTS = {
    "efas_local_regular": {
        "class": "ce",
        "stream": "efas",
        "type": "fc",
        "levtype": "sfc",
        "expver": "0001",
        "origin": "ecmf",
        "domain": "g",
        "model": "lisflood",
        "date": "20240101",
        "time": "0000",
        "step": "6",
        "param": "240023",
    },
    "healpix_1024": {
        "activity": "projections",
        "class": "d1",
        "dataset": "climate-dt",
        "experiment": "ssp3-7.0",
        "expver": "0001",
        "generation": "1",
        "model": "ifs-nemo",
        "realization": "1",
        "resolution": "high",
        "type": "fc",
        "stream": "clte",
        "levtype": "sfc",
        "date": "20200101",
        "time": "0000",
        "param": "167",
    },
    "octahedral_1280": {
        "class": "od",
        "stream": "oper",
        "type": "fc",
        "levtype": "sfc",
        "expver": "0001",
        "domain": "g",
        "date": "20240101",
        "time": "0000",
        "step": "0",
        "param": "167",
    },
}

#: name -> (grid, ("box", lower, upper) | ("polygon", vertices))
SHAPES = {
    "efas_danube_box": ("efas_local_regular", ("box", [42.08, 8.15], [50.25, 29.73])),
    "healpix1024_europe_box": ("healpix_1024", ("box", [34, -25], [72, 45])),
    "healpix1024_europe_polygon": ("healpix_1024", ("polygon", EUROPE_POLYGON)),
    "efas_europe_polygon": ("efas_local_regular", ("polygon", EUROPE_POLYGON)),
    "healpix1024_global_box": ("healpix_1024", ("box", [-90, -180], [90, 180])),
    # the whole EFAS local_regular domain
    "efas_domain_box": (
        "efas_local_regular",
        ("box", [22.758333333333333, -25.241666666666667], [72.24166666666666, 50.24166666666667]),
    ),
    "o1280_global_box": ("octahedral_1280", ("box", [-90, -180], [90, 180])),
}


def rss_bytes():
    return int(open("/proc/self/statm").read().split()[1]) * os.sysconf("SC_PAGE_SIZE")


def peak_bytes():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def tree_bytes(tree):
    """``getsizeof`` estimate of a tree: nodes, their ``__dict__``s and their values."""
    total = 0
    stack = [tree]
    while stack:
        node = stack.pop()
        total += sys.getsizeof(node) + sys.getsizeof(node.__dict__)
        values = getattr(node, "values", ())
        total += sys.getsizeof(values)
        if isinstance(values, tuple):
            total += sum(sys.getsizeof(v) for v in values)
        for name in ("coordinates", "indexes", "tag_ids"):
            array = getattr(node, name, None)
            total += getattr(array, "nbytes", 0)
        stack.extend(node.children)
    return total


def point_count(tree):
    total = 0
    for leaf in tree.leaves:
        total += getattr(leaf, "point_count", None) or len(leaf.values)
    return total


def build_request(grid, shape_spec):
    import pandas as pd
    from polytope_mars.testing import fake_gribjump_config_dict

    from polytope_feature.polytope import Request
    from polytope_feature.shapes import Box, Polygon, Select, Union

    request = dict(REQUESTS[grid])
    config = fake_gribjump_config_dict(grid, {**request, "feature": {"type": "boundingbox"}})
    options = config["options"]
    merged = any(
        transformation.get("name") == "merge"
        for axis in options["axis_config"]
        if axis["axis_name"] == "date"
        for transformation in axis["transformations"]
    )
    selects = []
    for key, value in request.items():
        if key == "date" and merged:
            selects.append(Select("date", [pd.Timestamp(f"{value}T{request['time']}")]))
        elif key == "time" and merged:
            continue
        elif key == "step":
            selects.append(Select("step", [int(value)]))
        else:
            selects.append(Select(key, [value]))
    if shape_spec[0] == "box":
        shape = Box(["latitude", "longitude"], shape_spec[1], shape_spec[2])
    else:
        shape = Union(["latitude", "longitude"], Polygon(["latitude", "longitude"], shape_spec[1]))
    return options, Request(*selects, shape)


def measure(name, bulk):
    from polytope_mars.testing import make_fake_gribjump

    from polytope_feature.polytope import Polytope

    grid, shape_spec = SHAPES[name]
    options, request = build_request(grid, shape_spec)
    options["bulk_grid_leaves"] = bulk
    gribjump = make_fake_gribjump(grid)

    api = Polytope(datacube=gribjump, options=options)
    # polytope-mars keeps one longitude leaf per latitude node for polygons
    api._merge_union_rows = True
    datacube = api.datacube
    datacube.check_branching_axes(request)
    api.switch_polytope_dim(request)
    datacube.nearest_search = {}

    gc.collect()
    before_slice = rss_bytes()
    start = time.perf_counter()
    tree = api.slice(datacube, request.polytopes())
    slice_s = time.perf_counter() - start
    gc.collect()
    after_slice = rss_bytes()
    sliced_leaves = len(tree.leaves)
    sliced_bytes = tree_bytes(tree)
    sliced_points = point_count(tree)

    start = time.perf_counter()
    datacube.prepare(tree)
    prepare_s = time.perf_counter() - start
    planning_s = datacube.prototype_metrics["request_planning_s"]

    start = time.perf_counter()
    datacube.get(tree)
    get_s = time.perf_counter() - start
    gc.collect()
    after_get = rss_bytes()
    points = point_count(tree)
    ranges = datacube.prototype_metrics["ranges_per_field"]

    return {
        "shape": name,
        "grid": grid,
        "bulk": bulk,
        "points": points,
        "sliced_points": sliced_points,
        "leaves_after_slice": sliced_leaves,
        "leaves_after_prepare": len(tree.leaves),
        "slice_s": round(slice_s, 2),
        "tree_rss_mb": round((after_slice - before_slice) / MiB, 1),
        "tree_bytes_per_point": round(sliced_bytes / max(sliced_points, 1), 1),
        "prepare_s": round(prepare_s, 2),
        "planning_s": round(planning_s, 2),
        "get_s": round(get_s, 2),
        "growth_bytes_per_point": round((after_get - after_slice) / max(points, 1), 1),
        "peak_growth_bytes_per_point": round((peak_bytes() - after_slice) / max(points, 1), 1),
        "peak_mb": round(peak_bytes() / MiB, 1),
        "ranges_per_field": ranges,
    }


COLUMNS = [
    ("shape", "shape", "{}"),
    ("bulk", "bulk", "{}"),
    ("points", "points", "{:,}"),
    ("slice s", "slice_s", "{}"),
    ("tree MB", "tree_rss_mb", "{}"),
    ("tree B/pt", "tree_bytes_per_point", "{}"),
    ("prepare s", "prepare_s", "{}"),
    ("planning s", "planning_s", "{}"),
    ("get s", "get_s", "{}"),
    ("growth B/pt", "growth_bytes_per_point", "{}"),
    ("peak growth B/pt", "peak_growth_bytes_per_point", "{}"),
    ("peak MB", "peak_mb", "{}"),
    ("ranges/field", "ranges_per_field", "{:,}"),
]


def table(rows):
    header = [label for label, _, _ in COLUMNS]
    body = [[fmt.format(row[key]) for _, key, fmt in COLUMNS] for row in rows]
    widths = [max(len(header[i]), *(len(line[i]) for line in body)) for i in range(len(header))]
    out = ["| " + " | ".join(h.ljust(w) for h, w in zip(header, widths)) + " |"]
    out.append("| " + " | ".join("-" * w for w in widths) + " |")
    for line in body:
        out.append("| " + " | ".join(c.ljust(w) for c, w in zip(line, widths)) + " |")
    return "\n".join(out)


def run_child(name, bulk):
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--child", name, "1" if bulk else "0"],
        capture_output=True,
        text=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            return json.loads(line)
    sys.stderr.write(proc.stdout + proc.stderr)
    raise RuntimeError(f"{name} (bulk={bulk}) failed")


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("shapes", nargs="*", default=[])
    parser.add_argument("--child", nargs=2, metavar=("SHAPE", "BULK"))
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.child:
        print(json.dumps(measure(args.child[0], args.child[1] == "1")))
        return 0

    rows = []
    for name in args.shapes or list(SHAPES):
        for bulk in (False, True):
            row = run_child(name, bulk)
            rows.append(row)
            if args.json:
                print(json.dumps(row), flush=True)
            else:
                print(f"  {name} bulk={bulk}: {row['points']:,} points", flush=True)
    if not args.json:
        print()
        print(table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
