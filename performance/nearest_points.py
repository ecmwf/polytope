"""Measure slice + ``prepare`` of a timeseries request with N nearest points, batched and per query.

Drives the real ``FDBDatacube`` against polytope-mars' fake gribjump (``polytope_mars.testing``), so the grids
and mapper options are the ones the deployments use, with pseudo-random points over the globe.  Every row runs
in a fresh subprocess; peak memory is ``ru_maxrss`` of that process (about 126 MB of it is the interpreter,
numpy and polytope baseline).

    python performance/nearest_points.py                            # the table in MEASUREMENTS.md
    python performance/nearest_points.py --n 1000 10000             # chosen sizes
    python performance/nearest_points.py --path old --n 1000        # the per-query path only
    python performance/nearest_points.py --json

The request is one field per grid, as ``performance/bulk_memory.py`` declares it: neither the slice nor
``prepare`` depends on how many instants the timeseries has, because the time axis is compressed and the
spatial sub-tree is built once.

``--path new`` resolves every nearest point of the request in one pass
(:mod:`polytope_feature.engine.nearest_grid`); ``--path old`` switches the batching off, which leaves the path
this replaced: one tree descent per point, then ``FDBDatacube.nearest_lat_lon_search`` sorting all candidates of
the request once per point.  That one is O(N^2) -- 370 s of ``prepare`` for 10 000 points on O1280 -- so
``--path old`` above a few thousand points takes a while.

Columns: the points asked for, the points the request came back with (several requested points can be nearest
to the same grid point), slice and ``prepare`` time, the index ranges one field asks gribjump for, and the
process peak.
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

#: grid name in polytope_mars.testing -> label
GRIDS = {"octahedral_1280": "O1280", "healpix_1024": "HEALPix nested 1024"}

DEFAULT_SIZES = (1000, 10000, 100000)


def peak_bytes():
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * 1024


def query_points(n, seed=11):
    """``n`` pseudo-random (latitude, longitude) points, longitudes on both sides of the seam."""
    import numpy as np

    rng = np.random.default_rng(seed)
    return rng.uniform([-89.0, -180.0], [89.0, 180.0], size=(n, 2)).tolist()


def measure(grid, n, batched, seed=11):
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from bulk_memory import build_request
    from polytope_mars.testing import make_fake_gribjump

    from polytope_feature.polytope import Polytope

    options, request = build_request(grid, ("points", query_points(n, seed)))
    api = Polytope(datacube=make_fake_gribjump(grid), options=options)
    # polytope-mars keeps one longitude leaf per latitude node where it can
    api._merge_union_rows = True
    datacube = api.datacube
    if not batched:
        # the per-query path: with no axes to batch, Points stay 1-D per axis and the nearest search runs
        datacube._nearest_grid_axes = (None,)
    datacube.check_branching_axes(request)
    api.switch_polytope_dim(request)
    datacube.nearest_search = {}
    for polytope in request.polytopes():
        if polytope.method == "nearest":
            query = polytope.values if polytope.is_flat else polytope.points
            points, _, tags = datacube.nearest_search.setdefault(tuple(polytope.axes()), ([], polytope.k, []))
            points.extend(list(point) for point in query)
            tags.extend([polytope.tag] * len(query))

    gc.collect()
    start = time.perf_counter()
    tree = api.slice(datacube, request.polytopes())
    slice_s = time.perf_counter() - start

    start = time.perf_counter()
    prepared = datacube.prepare(tree)
    prepare_s = time.perf_counter() - start

    nodes = prepared.leaves
    return {
        "grid": GRIDS[grid],
        "path": "new" if batched else "old",
        "requested": n,
        "points": sum(node.point_count for node in nodes),
        "spatial_nodes": len(nodes),
        "slice_s": round(slice_s, 2),
        "prepare_s": round(prepare_s, 2),
        "total_s": round(slice_s + prepare_s, 2),
        "ranges_per_field": datacube.prototype_metrics["ranges_per_field"],
        "peak_mb": round(peak_bytes() / MiB, 1),
    }


COLUMNS = [
    ("grid", "grid", "{}"),
    ("path", "path", "{}"),
    ("requested", "requested", "{:,}"),
    ("points", "points", "{:,}"),
    ("slice s", "slice_s", "{}"),
    ("prepare s", "prepare_s", "{}"),
    ("total s", "total_s", "{}"),
    ("ranges/field", "ranges_per_field", "{:,}"),
    ("peak MB", "peak_mb", "{}"),
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


def run_child(grid, n, path):
    proc = subprocess.run(
        [sys.executable, os.path.abspath(__file__), "--child", grid, "--n", str(n), "--path", path],
        capture_output=True,
        text=True,
    )
    for line in proc.stdout.splitlines():
        if line.startswith("{"):
            return json.loads(line)
    sys.stderr.write(proc.stdout + proc.stderr)
    raise RuntimeError(f"{grid} n={n} path={path} failed")


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("--grid", action="append", choices=sorted(GRIDS), default=None)
    parser.add_argument("--n", type=int, nargs="+", default=list(DEFAULT_SIZES))
    parser.add_argument("--path", action="append", choices=["new", "old"], default=None)
    parser.add_argument("--child", metavar="GRID")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    if args.child:
        print(json.dumps(measure(args.child, args.n[0], args.path == ["new"])))
        return 0

    rows = []
    for grid in args.grid or sorted(GRIDS):
        for n in args.n:
            for path in args.path or ["new"]:
                row = run_child(grid, n, path)
                rows.append(row)
                if args.json:
                    print(json.dumps(row), flush=True)
                else:
                    print(f"  {row['grid']} {path} n={n:,}: {row['total_s']} s", flush=True)
    if not args.json:
        print()
        print(table(rows))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
