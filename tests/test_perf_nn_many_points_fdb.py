"""
Performance test: retrieve nearest-neighbour values for a large number of query points.

This exercises the k_nearest_neighbor / nearest_neighbor path in QuadTreeSlicer,
which was the primary performance bottleneck before the fix that stored the point
cloud inside the QuadTree struct rather than passing it via the FFI on every call.

Run with:
    pytest tests/test_perf_nn_many_points_fdb.py -v -s -m fdb

Each test prints elapsed wall-clock time for the retrieve() call and the number of
leaves returned, so you can compare timings before/after across builds.
"""

import math
import time

import numpy as np
import pandas as pd
import pytest

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select, Union

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_union_of_points(latlons, k=1):
    """Build a flat Union of Point(nearest) shapes from a list of (lat, lon) pairs."""
    shapes = [Point(["latitude", "longitude"], [[lat, lon]], method="nearest", k=k) for lat, lon in latlons]
    if len(shapes) == 1:
        return shapes[0]
    # Use the variadic form to keep the Union flat — avoids deep recursion
    # that a chained binary Union would cause for large N.
    return Union(["latitude", "longitude"], *shapes)


def _grid_query_points(n_lat, n_lon, lat_lo, lat_hi, lon_lo, lon_hi):
    """Return an (n_lat * n_lon) list of (lat, lon) query points on a regular grid."""
    lats = np.linspace(lat_lo, lat_hi, n_lat)
    lons = np.linspace(lon_lo, lon_hi, n_lon)
    return [(float(la), float(lo)) for la in lats for lo in lons]


# ---------------------------------------------------------------------------
# Options shared across tests
# ---------------------------------------------------------------------------

LAMBERT_LAM_OPTIONS = {
    "axis_config": [
        {
            "axis_name": "step",
            "transformations": [{"name": "type_change", "type": "int"}],
        },
        {
            "axis_name": "date",
            "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        },
        {
            "axis_name": "values",
            "transformations": [
                {
                    "name": "mapper",
                    "type": "lambert_conformal",
                    "resolution": 0,
                    "axes": ["latitude", "longitude"],
                    "md5_hash": "3c528b5fd68ca692a8922cbded813465",
                    "is_spherical": True,
                    "radius": 6371229,
                    "nv": 0,
                    "nx": 1489,
                    "ny": 1489,
                    "LoVInDegrees": 1.93697,
                    "Dx": 500,
                    "Dy": 500,
                    "latFirstInRadians": ((43.6409 + 2.9710306719721302e-05) / 180) * math.pi,
                    "lonFirstInRadians": ((357.32 - 0.00024761029651987343) / 180) * math.pi,
                    "LoVInRadians": (1.93697 / 180) * math.pi,
                    "Latin1InRadians": (47.082971 / 180) * math.pi,
                    "Latin2InRadians": (47.082971 / 180) * math.pi,
                    "LaDInRadians": (47.082971 / 180) * math.pi,
                }
            ],
        },
    ],
    "pre_path": {"date": "20250221"},
    "engine_options": {
        "step": "hullslicer",
        "date": "hullslicer",
        "levtype": "hullslicer",
        "param": "hullslicer",
        "latitude": "quadtree",
        "longitude": "quadtree",
    },
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNNManyPointsPerf:
    """Performance tests for nearest-neighbour retrieval over many query points."""

    def _build_api(self):
        import pygribjump as gj

        fdbdatacube = gj.GribJump()
        return Polytope(datacube=fdbdatacube, options=LAMBERT_LAM_OPTIONS)

    def _base_selects(self):
        return [
            Select("date", [pd.Timestamp("20250221T0000")]),
            Select("step", [0]),
            Select("param", ["130"]),
            Select("levtype", ["sfc"]),
        ]

    def _run(self, capsys, label, query_points, k):
        api = self._build_api()
        shape = _make_union_of_points(query_points, k=k)
        request = Request(*self._base_selects(), shape)

        t0 = time.perf_counter()
        result = api.retrieve(request)
        elapsed = time.perf_counter() - t0

        n_leaves = len(result.leaves)
        with capsys.disabled():
            print(f"\n{label}  query_pts={len(query_points)}  k={k}  leaves={n_leaves}  elapsed={elapsed:.3f}s")

        assert n_leaves > 0, f"Expected at least one result leaf, got {n_leaves}"
        return n_leaves, elapsed

    # ------------------------------------------------------------------
    # k=1  (exercises nearest_neighbor)
    # ------------------------------------------------------------------

    @pytest.mark.fdb
    def test_nn_10_points(self, capsys):
        pts = _grid_query_points(2, 5, 44.0, 44.5, 5.0, 6.0)
        self._run(capsys, "[k=1]", pts, k=1)

    @pytest.mark.fdb
    def test_nn_100_points(self, capsys):
        pts = _grid_query_points(10, 10, 44.0, 45.0, 5.0, 6.5)
        self._run(capsys, "[k=1]", pts, k=1)

    @pytest.mark.fdb
    def test_nn_500_points(self, capsys):
        pts = _grid_query_points(20, 25, 44.0, 46.0, 4.5, 7.5)
        self._run(capsys, "[k=1]", pts, k=1)

    @pytest.mark.fdb
    def test_nn_1000_points(self, capsys):
        pts = _grid_query_points(40, 25, 44.0, 47.0, 4.0, 8.0)
        self._run(capsys, "[k=1]", pts, k=1)

    # ------------------------------------------------------------------
    # k=4  (exercises k_nearest_neighbor — the primary FFI-copy fix)
    # ------------------------------------------------------------------

    @pytest.mark.fdb
    def test_nn_100_points_k4(self, capsys):
        pts = _grid_query_points(10, 10, 44.0, 45.0, 5.0, 6.5)
        self._run(capsys, "[k=4]", pts, k=4)

    @pytest.mark.fdb
    def test_nn_500_points_k4(self, capsys):
        pts = _grid_query_points(20, 25, 44.0, 46.0, 4.5, 7.5)
        self._run(capsys, "[k=4]", pts, k=4)
