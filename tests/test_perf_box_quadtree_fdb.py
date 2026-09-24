"""
Performance test: retrieve values inside progressively larger axis-aligned
lat/lon boxes on an unstructured (Lambert LAM) datacube.

This exercises the ``query_polygon`` path in ``QuadTreeSlicer`` which recurses
through the quadtree, splitting the query polygon at each level.

The interesting property of *box* queries (as opposed to nearest-neighbour
queries) is that a large box can fully contain entire quadtree subtrees.  A
well-implemented quadtree extractor should:

* skip subtrees whose bounding box is disjoint from the query box, and
* harvest **all** points in subtrees whose bounding box lies entirely inside
  the query box (no per-point containment check needed).

Any implementation that recurses down to leaves and runs a per-point
``is_contained_in`` for large boxes will scale roughly linearly in the number
of points inside the box.  With the two prunes above, cost should scale with
the perimeter of the box (i.e. the number of quadrants the box boundary
crosses), plus the number of returned points.

Run with:
    pytest tests/test_perf_box_quadtree_fdb.py -v -s -m fdb

Each test prints elapsed wall-clock time for the ``retrieve()`` call, the
number of leaves returned, and the area of the query box, so timings can be
compared across builds.
"""

import math
import time

import pandas as pd
import pytest

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select

# ---------------------------------------------------------------------------
# Options shared across tests (identical to test_perf_nn_many_points_fdb.py)
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


class TestBoxQuadTreePerf:
    """Performance tests for box (axis-aligned rectangle) retrieval on the quadtree slicer."""

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

    def _run(self, capsys, label, lat_lo, lat_hi, lon_lo, lon_hi):
        api = self._build_api()
        box = Box(
            ["latitude", "longitude"],
            lower_corner=[lat_lo, lon_lo],
            upper_corner=[lat_hi, lon_hi],
        )
        request = Request(*self._base_selects(), box)

        area = (lat_hi - lat_lo) * (lon_hi - lon_lo)

        t0 = time.perf_counter()
        result = api.retrieve(request)
        elapsed = time.perf_counter() - t0

        n_leaves = len(result.leaves)
        with capsys.disabled():
            print(
                f"\n{label}  bbox=[{lat_lo},{lat_hi}]x[{lon_lo},{lon_hi}]"
                f"  area={area:.3f}  leaves={n_leaves}  elapsed={elapsed:.3f}s"
            )

        assert n_leaves > 0, f"Expected at least one result leaf, got {n_leaves}"
        return n_leaves, elapsed

    # ------------------------------------------------------------------
    # Progressively larger boxes covering more of the Lambert LAM domain.
    # The domain spans roughly lat 43.6-49.7, lon 357.3-8.2 (Central/Western
    # Europe), so the boxes below stay inside it.
    # ------------------------------------------------------------------

    @pytest.mark.fdb
    def test_box_tiny(self, capsys):
        # ~ 0.25 deg square: small — should touch few quadtree nodes.
        self._run(capsys, "[box tiny]", 44.0, 44.25, 5.0, 5.25)

    @pytest.mark.fdb
    def test_box_small(self, capsys):
        # ~ 1 deg square.
        self._run(capsys, "[box small]", 44.0, 45.0, 5.0, 6.0)

    @pytest.mark.fdb
    def test_box_medium(self, capsys):
        # ~ 2 x 3 deg.
        self._run(capsys, "[box medium]", 44.0, 46.0, 4.5, 7.5)

    @pytest.mark.fdb
    def test_box_large(self, capsys):
        # ~ 4 x 4 deg — begins to cover full quadtree subtrees interior to the
        # domain, so the "quadrant fully inside box" fast-path should kick in.
        self._run(capsys, "[box large]", 44.0, 48.0, 3.0, 7.0)

    @pytest.mark.fdb
    def test_box_huge(self, capsys):
        # Nearly full domain (staying on the eastern side of the 0/360 seam so
        # we don't exercise cyclic-longitude splitting here). Extraction time
        # should be dominated by the number of returned points, not by
        # per-quadrant slicing.
        self._run(capsys, "[box huge]", 43.7, 49.5, 0.5, 8.0)
