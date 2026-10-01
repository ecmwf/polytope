"""
Performance test: retrieve nearest-neighbour values for a large number of query points
on an octahedral (reduced Gaussian) grid.

This mirrors tests/test_perf_nn_many_points_fdb.py but swaps the Lambert-conformal
mapper for the octahedral mapper + quadtree engine, exercising the same
k_nearest_neighbor / nearest_neighbor path in QuadTreeSlicer for a different grid type.

Run with:
    pytest tests/test_perf_nn_many_points_octahedral_fdb.py -v -s -m fdb

Each test prints elapsed wall-clock time for the retrieve() call and the number of
leaves returned, so you can compare timings before/after across builds, and across
grid types (octahedral vs lambert_conformal).
"""

import time

import numpy as np
import pandas as pd
import pytest

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_union_of_points(latlons, k=1):
    """Build a flat Point(nearest) shape from a list of (lat, lon) pairs."""
    latlons = [[lat, lon] for lat, lon in latlons]
    return Point(["latitude", "longitude"], latlons, method="nearest", k=k)


def _grid_query_points(n_lat, n_lon, lat_lo, lat_hi, lon_lo, lon_hi):
    """Return an (n_lat * n_lon) list of (lat, lon) query points on a regular grid."""
    lats = np.linspace(lat_lo, lat_hi, n_lat)
    lons = np.linspace(lon_lo, lon_hi, n_lon)
    return [(float(la), float(lo)) for la in lats for lo in lons]


# ---------------------------------------------------------------------------
# Options shared across tests
# ---------------------------------------------------------------------------

OCTAHEDRAL_OPTIONS = {
    "axis_config": [
        {
            "axis_name": "step",
            "transformations": [{"name": "type_change", "type": "int"}],
        },
        {
            "axis_name": "number",
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
                    "type": "octahedral",
                    "resolution": 1280,
                    "axes": ["latitude", "longitude"],
                }
            ],
        },
        {
            "axis_name": "latitude",
            "transformations": [{"name": "reverse", "is_reverse": True}],
        },
        {
            "axis_name": "longitude",
            "transformations": [{"name": "cyclic", "range": [0, 360]}],
        },
    ],
    "compressed_axes_config": [
        "longitude",
        "latitude",
        "levtype",
        "step",
        "date",
        "domain",
        "expver",
        "param",
        "class",
        "stream",
        "type",
    ],
    "pre_path": {
        "class": "od",
        "expver": "0001",
        "levtype": "sfc",
        "stream": "oper",
    },
    # No "engine_options" override: the octahedral/reduced-Gaussian mapper is
    # not an irregular point cloud (is_irregular=False), so it is handled by
    # HullSlicer on every axis including latitude/longitude, not QuadTreeSlicer
    # (which requires a genuine unstructured point cloud, e.g. lambert_conformal
    # or icon). All axes default to "hullslicer" when no engine_options is given.
}


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestNNManyPointsOctahedralPerf:
    """Performance tests for nearest-neighbour retrieval over many query points
    against an octahedral grid served from FDB."""

    def _build_api(self):
        import pygribjump as gj

        fdbdatacube = gj.GribJump()
        return Polytope(datacube=fdbdatacube, options=OCTAHEDRAL_OPTIONS)

    def _base_selects(self):
        return [
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230625T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
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
        n_leaves, time_taken = self._run(capsys, "[k=1]", pts, k=1)
        print("IT TOOK", time_taken, "SECONDS TO RETRIEVE", n_leaves, "LEAVES FOR 10 POINTS")

    @pytest.mark.fdb
    def test_nn_100_points(self, capsys):
        pts = _grid_query_points(10, 10, 44.0, 45.0, 5.0, 6.5)
        n_leaves, time_taken = self._run(capsys, "[k=1]", pts, k=1)
        print("IT TOOK", time_taken, "SECONDS TO RETRIEVE", n_leaves, "LEAVES FOR 100 POINTS")

    @pytest.mark.fdb
    def test_nn_500_points(self, capsys):
        pts = _grid_query_points(20, 25, 44.0, 46.0, 4.5, 7.5)
        n_leaves, time_taken = self._run(capsys, "[k=1]", pts, k=1)
        print("IT TOOK", time_taken, "SECONDS TO RETRIEVE", n_leaves, "LEAVES FOR 500 POINTS")

    @pytest.mark.fdb
    def test_nn_1000_points(self, capsys):
        pts = _grid_query_points(40, 25, 44.0, 47.0, 4.0, 8.0)
        n_leaves, time_taken = self._run(capsys, "[k=1]", pts, k=1)
        print("IT TOOK", time_taken, "SECONDS TO RETRIEVE", n_leaves, "LEAVES FOR 1000 POINTS")

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
