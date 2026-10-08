"""Check that folding the spatial layers into a bulk node changes neither the point order nor the values.

For every case of polytope-mars' golden corpus (``../polytope-mars/tests/golden/cases/*.yaml``) the request
is sliced and fetched twice against the same fake datacube -- once with ``bulk_grid_leaves`` off, once with it
on -- and the ordered ``(latitude, longitude)`` list and the per-field values are compared.  Equality here is
what makes the CovJSON bytes of the two paths identical, so a case that differs is a bug to report, not
something to paper over.

    python performance/bulk_order.py                  # every case
    python performance/bulk_order.py CASE [...]       # named cases
    python performance/bulk_order.py -v               # list the cases and their point counts

Needs polytope-mars importable (it provides the fake datacube, the grids and the feature -> shapes mapping).
"""

import argparse
import itertools
import os
import sys

import numpy as np

CASES_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "polytope-mars", "tests", "golden", "cases"
)


def _is_bulk(node):
    from polytope_feature.datacube.tensor_index_tree import BulkMergedTensorIndexNode

    return isinstance(node, BulkMergedTensorIndexNode)


def _is_merged(node):
    from polytope_feature.datacube.tensor_index_tree import MergedTensorIndexNode

    return isinstance(node, MergedTensorIndexNode)


def _walk(node, ancestors=()):
    yield node, ancestors
    for child in node.children:
        yield from _walk(child, ancestors + (child,))


def _as_float(values):
    """A node's result block as float64, with the ``None``s of a missing field as NaN."""
    array = np.asarray(values, dtype=object)
    return np.array([np.nan if v is None else float(v) for v in array], dtype=np.float64)


def field_points(tree):
    """``{field: [(lat, lon, value), ...]}`` of a filled tree, in traversal order.

    ``field`` is the tuple of ``(axis, value)`` pairs of the non-spatial axes above the leaf, following the
    ``itertools.product`` layout of a compressed leaf's ``result``.
    """
    out = {}
    for node, ancestors in _walk(tree):
        if node is tree or len(node.children) != 0:
            continue
        if _is_bulk(node):
            field_nodes = ancestors[:-1]
            coordinates = node.coordinates
            combos = list(itertools.product(*[n.values for n in field_nodes]))
            blocks = [_as_float(values) for values in node.result]
        elif _is_merged(node):
            # one legacy merged (lat, lon) leaf per point, one value per field in its result
            field_nodes = ancestors[:-1]
            coordinates = [(node.values[0], node.values[1])]
            combos = list(itertools.product(*[n.values for n in field_nodes]))
            values = _as_float(node.result)
            blocks = [values[i : i + 1] for i in range(len(combos))]  # noqa: E203
        else:
            field_nodes, lat_node = ancestors[:-2], ancestors[-2]
            lons = np.asarray(node.values, dtype=np.float64)
            coordinates = np.column_stack((np.full(lons.shape, float(lat_node.values[0])), lons))
            combos = list(itertools.product(*[n.values for n in field_nodes]))
            n = len(coordinates)
            values = _as_float(node.result)
            blocks = [values[i * n : (i + 1) * n] for i in range(len(combos))]  # noqa: E203
        for combo, block in zip(combos, blocks):
            field = tuple((n_.axis.name, v) for n_, v in zip(field_nodes, combo))
            points = out.setdefault(field, [])
            for (lat, lon), value in zip(coordinates, block):
                points.append((round(float(lat), 9), round(float(lon), 9), float(value)))
    return out


def run(case, bulk):
    from polytope_mars.testing.golden import build_fake, make_polytope_mars

    fake = build_fake(case, missing_mode="empty")
    pm, request = make_polytope_mars(case, fake)
    pm.conf.options.bulk_grid_leaves = bulk
    extractor = pm._prepare_extraction(request)
    api, tree = extractor._slice()
    datacube = api.datacube
    datacube.prepare(tree)
    datacube.get(tree)
    return field_points(tree)


def same(a, b):
    if a is None or b is None:
        return a is b
    return a == b or (np.isnan(a) and np.isnan(b))


def compare(name, path, verbose=False):
    from polytope_mars.testing.golden import load_case

    case = load_case(path)
    if case.get("expect_error"):
        print(f"{name:34s} skipped (expects an error)")
        return True
    off = run(case, False)
    on = run(case, True)
    n_points = sum(len(points) for points in off.values())
    if list(off) != list(on):
        print(f"{name:34s} DIFFERS: fields {list(off)} != {list(on)}")
        return False
    for field, points in off.items():
        other = on[field]
        if len(points) != len(other):
            print(f"{name:34s} DIFFERS: {len(points)} points != {len(other)} for field {field}")
            return False
        for i, (left, right) in enumerate(zip(points, other)):
            if left[:2] != right[:2] or not same(left[2], right[2]):
                print(f"{name:34s} DIFFERS: point {i} of field {field}: {left} != {right}")
                return False
    if verbose:
        print(f"{name:34s} identical ({len(off)} fields, {n_points} values)")
    return True


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument("cases", nargs="*", default=[])
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)

    names = args.cases or sorted(f[:-5] for f in os.listdir(CASES_DIR) if f.endswith(".yaml"))
    failed = []
    for name in names:
        if not compare(name, os.path.join(CASES_DIR, f"{name}.yaml"), args.verbose):
            failed.append(name)
    print()
    if failed:
        print(f"{len(failed)} of {len(names)} cases differ: {', '.join(failed)}")
        return 1
    print(f"all {len(names)} golden cases give the same ordered points and values with and without the fold")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
