"""
Tests for cyclic-axis handling on unstructured (irregular / quadtree) grids.

When a request polygon straddles the cyclic longitude seam (e.g. a Box from
lon=355° to lon=370° on a [0°, 360°] axis) the engine must split the polygon
at the cyclic boundary, query each fragment separately against the point cloud,
and return the union of results.

The test uses a tiny synthetic point cloud so that no external data files are
needed.
"""

import numpy as np
import xarray as xr

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box

# ---------------------------------------------------------------------------
# Shared fixture helpers
# ---------------------------------------------------------------------------

# Seven synthetic lat/lon points:
#   idx 0-2  : just *before* the 0°/360° seam  (lon ≈ 357–359)
#   idx 3-5  : just *after* the seam            (lon ≈ 1–3)
#   idx 6    : far away                         (lon = 180)
LATS = [5.0, 5.0, 5.0, 5.0, 5.0, 5.0, 50.0]
LONS = [357.0, 358.0, 359.0, 1.0, 2.0, 3.0, 180.0]
POINTS = list(zip(LATS, LONS))


def _make_api(engine: str = "quadtree") -> Polytope:
    arr = xr.DataArray(np.zeros(len(POINTS)), dims=["values"])
    options = {
        "axis_config": [
            {
                "axis_name": "values",
                "transformations": [
                    {
                        "name": "mapper",
                        "type": "unstructured",
                        "axes": ["latitude", "longitude"],
                        "points": POINTS,
                    }
                ],
            },
            {
                "axis_name": "longitude",
                "transformations": [{"name": "cyclic", "range": [0, 360]}],
            },
        ],
        "engine_options": {
            "latitude": engine,
            "longitude": engine,
        },
    }
    return Polytope(datacube=arr, options=options)


def _retrieved_lons(result) -> set:
    lons = set()
    for leaf in result.leaves:
        flat = leaf.flatten()
        if "longitude" in flat:
            lons.add(flat["longitude"][0])
    return lons


# ---------------------------------------------------------------------------
# QuadTree engine tests
# ---------------------------------------------------------------------------


class TestQuadtreeCyclicUnstructured:
    """Quadtree engine: verify cyclic-seam polygon splitting."""

    def setup_method(self, method):
        self.api = _make_api("quadtree")

    def test_box_crossing_seam_at_360(self):
        """Box from lon=355 to lon=370 must return points on both sides of the seam."""
        request = Request(Box(["latitude", "longitude"], [0, 355], [10, 370]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        # Should find the three points just before the seam and the three just after.
        assert lons == {357.0, 358.0, 359.0, 1.0, 2.0, 3.0}
        # The far-away point at lon=180 must NOT be returned.
        assert 180.0 not in lons

    def test_box_crossing_seam_with_negative_longitude(self):
        """Box with negative lower longitude [-5, 5] also straddles the seam."""
        request = Request(Box(["latitude", "longitude"], [0, -5], [10, 5]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        # -5 maps to 355 in [0, 360], so the covered range is [355, 360] ∪ [0, 5].
        assert lons == {357.0, 358.0, 359.0, 1.0, 2.0, 3.0}

    def test_box_not_crossing_seam(self):
        """A Box that stays on one side of the seam should not be split."""
        request = Request(Box(["latitude", "longitude"], [0, 356], [10, 360]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {357.0, 358.0, 359.0}
        # Points just after the seam must NOT be returned.
        for lon in [1.0, 2.0, 3.0]:
            assert lon not in lons

    def test_box_far_from_seam(self):
        """A Box in the middle of the range returns only the matching far-away point."""
        request = Request(Box(["latitude", "longitude"], [40, 170], [60, 190]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {180.0}

    def test_box_covering_full_longitude_range(self):
        """A Box spanning all longitudes [0, 360] should return all points."""
        request = Request(Box(["latitude", "longitude"], [0, 0], [60, 360]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {357.0, 358.0, 359.0, 1.0, 2.0, 3.0, 180.0}

    def test_box_shifted_beyond_360(self):
        """Longitudes supplied entirely above 360 are remapped and still work."""
        # [361, 365] maps to [1, 5] in canonical space.
        request = Request(Box(["latitude", "longitude"], [0, 361], [10, 365]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {1.0, 2.0, 3.0}

    def test_no_results_outside_any_point(self):
        """A Box with no matching points returns an empty result."""
        request = Request(Box(["latitude", "longitude"], [0, 10], [10, 20]))
        result = self.api.retrieve(request)

        assert _retrieved_lons(result) == set()


# ---------------------------------------------------------------------------
# PointInPolygon engine tests (same scenarios)
# ---------------------------------------------------------------------------


class TestPointInPolygonCyclicUnstructured:
    """Point-in-polygon engine: same cyclic-seam scenarios."""

    def setup_method(self, method):
        self.api = _make_api("point_in_polygon")

    def test_box_crossing_seam_at_360(self):
        request = Request(Box(["latitude", "longitude"], [0, 355], [10, 370]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {357.0, 358.0, 359.0, 1.0, 2.0, 3.0}

    def test_box_crossing_seam_with_negative_longitude(self):
        request = Request(Box(["latitude", "longitude"], [0, -5], [10, 5]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {357.0, 358.0, 359.0, 1.0, 2.0, 3.0}

    def test_box_not_crossing_seam(self):
        request = Request(Box(["latitude", "longitude"], [0, 356], [10, 360]))
        result = self.api.retrieve(request)

        lons = _retrieved_lons(result)
        assert lons == {357.0, 358.0, 359.0}


# ---------------------------------------------------------------------------
# Unit-level tests for DatacubeAxisCyclic.split_polytope_at_boundary
# ---------------------------------------------------------------------------


class TestSplitPolytopeAtBoundary:
    """Direct unit tests for the cyclic split helper, independent of any engine."""

    def _make_cyclic_axis_and_transform(self):
        from polytope_feature.datacube.transformations.datacube_cyclic.datacube_cyclic import (
            DatacubeAxisCyclic,
        )
        from polytope_feature.options import CyclicConfig

        cfg = CyclicConfig(name="cyclic", range=[0, 360])
        transform = DatacubeAxisCyclic("longitude", cfg)

        # Build a minimal axis stub that DatacubeAxisCyclic will interact with.
        class _Axis:
            range = [0, 360]
            tol = 1e-8

        axis = _Axis()
        return transform, axis

    def _box_polytope(self, lat_lo, lon_lo, lat_hi, lon_hi):
        from polytope_feature.shapes import Box

        return Box(["latitude", "longitude"], [lat_lo, lon_lo], [lat_hi, lon_hi]).polytope()[0]

    def test_in_range_returns_unchanged(self):
        transform, axis = self._make_cyclic_axis_and_transform()
        poly = self._box_polytope(0, 10, 10, 50)
        result = transform.split_polytope_at_boundary(poly, "longitude", axis)
        assert len(result) == 1
        assert result[0] is poly

    def test_seam_crossing_produces_two_fragments(self):
        transform, axis = self._make_cyclic_axis_and_transform()
        poly = self._box_polytope(0, 355, 10, 370)
        result = transform.split_polytope_at_boundary(poly, "longitude", axis)
        assert len(result) == 2

        # Collect all longitude coords from all fragments.
        all_lons = [pt[1] for frag in result for pt in frag.points]
        # All longitudes must now lie inside [0, 360].
        assert all(0 - axis.tol <= lon <= 360 + axis.tol for lon in all_lons)

    def test_negative_lon_crossing_zero_seam(self):
        transform, axis = self._make_cyclic_axis_and_transform()
        poly = self._box_polytope(0, -5, 10, 5)
        result = transform.split_polytope_at_boundary(poly, "longitude", axis)
        assert len(result) == 2

        all_lons = [pt[1] for frag in result for pt in frag.points]
        assert all(0 - axis.tol <= lon <= 360 + axis.tol for lon in all_lons)

    def test_entirely_above_360_remaps_without_split(self):
        transform, axis = self._make_cyclic_axis_and_transform()
        poly = self._box_polytope(0, 361, 10, 365)
        result = transform.split_polytope_at_boundary(poly, "longitude", axis)
        # No cyclic boundary within (361, 365), so just one remapped fragment.
        assert len(result) == 1
        all_lons = [pt[1] for pt in result[0].points]
        assert all(0 - axis.tol <= lon <= 360 + axis.tol for lon in all_lons)

    def test_axes_order_longitude_first(self):
        """Split works correctly when longitude is the first axis (not second)."""
        from polytope_feature.shapes import ConvexPolytope

        transform, axis = self._make_cyclic_axis_and_transform()
        # Polygon with axes = ["longitude", "latitude"], points = (lon, lat)
        poly = ConvexPolytope(
            ["longitude", "latitude"],
            [[355, 0], [370, 0], [370, 10], [355, 10]],
        )
        result = transform.split_polytope_at_boundary(poly, "longitude", axis)
        assert len(result) == 2
        all_lons = [pt[0] for frag in result for pt in frag.points]
        assert all(0 - axis.tol <= lon <= 360 + axis.tol for lon in all_lons)
