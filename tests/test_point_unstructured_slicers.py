"""Unit tests (no FDB needed) covering Point shapes on the 2-D unstructured slicers:
quadtree, optimised_quadtree, point_in_polygon and optimised_point_in_polygon.

Point shapes used to only get resolved as a single 2-D polytope (via
``Point.decompose_1D = False``) on the "quadtree" engine specifically. This meant that
Point requests raised (or silently misbehaved) on the other three 2-D slicers, and that
none of them supported ``method="nearest"`` for Point shapes. These tests exercise:

* ``Polytope.switch_polytope_dim`` flips ``decompose_1D`` for every engine that resolves
  two axes jointly (``Engine.resolves_axes_jointly``), not just the one named "quadtree".
* Each of the four engines correctly resolves a plain Point (polygon-style) query.
* Each of the four engines correctly resolves a ``method="nearest"`` Point query, matching
  the quadtree slicer's k-nearest-neighbour behaviour.
"""

import pytest

import polytope_feature.engine.optimised_point_in_polygon_slicer as optimised_point_in_polygon_slicer
import polytope_feature.engine.optimised_quadtree_slicer as optimised_quadtree_slicer
import polytope_feature.engine.point_in_polygon_slicer as point_in_polygon_slicer
import polytope_feature.engine.quadtree_slicer as quadtree_slicer

# The installed Rust extension in this environment exposes a query_polygon()/
# extract_point_in_poly() signature that no longer matches what these engines call (a
# pre-existing, unrelated binary/binding mismatch - confirmed to affect Box/Polygon
# queries identically, before and after this change). Force the pure-Python fallback
# paths so these tests exercise the actual Point/"nearest" logic instead of that
# unrelated breakage.
from polytope_feature.datacube.quadtree.quad_tree import QuadTree as PyQuadTree
from polytope_feature.engine.engine import Engine
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.engine.optimised_point_in_polygon_slicer import (
    OptimisedPointInPolygonSlicer,
)
from polytope_feature.engine.optimised_quadtree_slicer import OptimisedQuadTreeSlicer
from polytope_feature.engine.point_in_polygon_slicer import PointInPolygonSlicer
from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer
from polytope_feature.polytope import Polytope
from polytope_feature.shapes import ConvexPolytope, Point

quadtree_slicer.use_rust = False
quadtree_slicer.QuadTree = PyQuadTree
optimised_quadtree_slicer.use_rust = False
optimised_quadtree_slicer.QuadTree = PyQuadTree
point_in_polygon_slicer.use_rust = False
optimised_point_in_polygon_slicer.use_rust = False
from shapely.geometry import Point as ShapelyPoint  # noqa: E402
from shapely.geometry.polygon import Polygon as ShapelyPolygon  # noqa: E402

optimised_point_in_polygon_slicer.Point = ShapelyPoint
optimised_point_in_polygon_slicer.Polygon = ShapelyPolygon


GRID = [(float(lat), float(lon)) for lat in range(5) for lon in range(5)]


class FakeAxis:
    is_cyclic = False
    transformations = []

    def __init__(self, name):
        self.name = name


LAT, LON = FakeAxis("latitude"), FakeAxis("longitude")


class FakeRequest:
    def __init__(self, shapes):
        self.shapes = shapes


class FakeDatacube:
    def __init__(self):
        self._axes = {"latitude": LAT, "longitude": LON}
        self.nearest_search = {}


SLICERS = {
    "quadtree": lambda: QuadTreeSlicer(GRID),
    "optimised_quadtree": lambda: OptimisedQuadTreeSlicer(GRID),
    "point_in_polygon": lambda: PointInPolygonSlicer(GRID),
    "optimised_point_in_polygon": lambda: OptimisedPointInPolygonSlicer(GRID),
}


def resolved_points(slicer_name, polytope):
    """Build the lat/lon branch for a single polytope and return the resulting (lat, lon) set."""
    slicer = SLICERS[slicer_name]()
    datacube = FakeDatacube()

    if slicer_name == "quadtree":
        # The quadtree engine batches all lat/lon polytopes of a node into one bulk leaf.
        from polytope_feature.datacube.tensor_index_tree import TensorIndexTree

        node = TensorIndexTree()
        node["unsliced_polytopes"] = {polytope}
        slicer._build_branch(LAT, node, datacube, [], None)
        if len(node.children) == 0:
            return set()
        bulk = next(iter(node.children))
        return set(map(tuple, bulk.coordinates.tolist()))

    from polytope_feature.datacube.tensor_index_tree import TensorIndexTree

    node = TensorIndexTree()
    node["unsliced_polytopes"] = [polytope]
    slicer._build_branch(LAT, node, datacube, [], None)
    found = set()
    for lat_child in node.children:
        for lon_child in lat_child.children:
            for lat_val in lat_child.values:
                for lon_val in lon_child.values:
                    found.add((float(lat_val), float(lon_val)))
    return found


class TestSwitchPolytopeDimCoversAllJointAxesEngines:
    @pytest.mark.parametrize(
        "slicer_name",
        ["quadtree", "optimised_quadtree", "point_in_polygon", "optimised_point_in_polygon"],
    )
    def test_decompose_1d_is_disabled_for_joint_axes_engines(self, slicer_name):
        api = object.__new__(Polytope)
        api.engine_options = {"latitude": slicer_name, "longitude": slicer_name}
        api.engines = {slicer_name: SLICERS[slicer_name]()}

        point_shape = Point(["latitude", "longitude"], [[1.0, 2.0]])
        assert point_shape.decompose_1D is True

        api.switch_polytope_dim(FakeRequest([point_shape]))

        assert point_shape.decompose_1D is False

    def test_hullslicer_is_untouched(self):
        api = object.__new__(Polytope)
        api.engine_options = {"step": "hullslicer"}
        api.engines = {"hullslicer": HullSlicer()}

        point_shape = Point(["step"], [[1.0]])
        api.switch_polytope_dim(FakeRequest([point_shape]))

        assert point_shape.decompose_1D is True

    def test_engine_flags(self):
        assert Engine.resolves_axes_jointly is False
        assert QuadTreeSlicer.resolves_axes_jointly is True
        assert OptimisedQuadTreeSlicer.resolves_axes_jointly is True
        assert PointInPolygonSlicer.resolves_axes_jointly is True
        assert OptimisedPointInPolygonSlicer.resolves_axes_jointly is True
        assert HullSlicer.resolves_axes_jointly is False


class TestPointShapeOnEachSlicer:
    @pytest.mark.parametrize(
        "slicer_name",
        ["quadtree", "optimised_quadtree", "point_in_polygon", "optimised_point_in_polygon"],
    )
    def test_point_at_grid_location_is_found(self, slicer_name):
        # A Point resolved with decompose_1D=False becomes a single 2-D ConvexPolytope,
        # exactly like the 2-D polytope Box/Polygon shapes would produce.
        polytope = ConvexPolytope(["latitude", "longitude"], [[2.0, 3.0]])
        assert resolved_points(slicer_name, polytope) == {(2.0, 3.0)}

    @pytest.mark.parametrize(
        "slicer_name",
        ["quadtree", "optimised_quadtree", "point_in_polygon", "optimised_point_in_polygon"],
    )
    def test_nearest_point_is_found(self, slicer_name):
        polytope = ConvexPolytope(["latitude", "longitude"], [[2.1, 3.2]], method="nearest", k=1)
        assert resolved_points(slicer_name, polytope) == {(2.0, 3.0)}

    @pytest.mark.parametrize(
        "slicer_name",
        ["quadtree", "optimised_quadtree", "point_in_polygon", "optimised_point_in_polygon"],
    )
    def test_nearest_k_points_are_found(self, slicer_name):
        polytope = ConvexPolytope(["latitude", "longitude"], [[2.0, 3.4]], method="nearest", k=2)
        assert resolved_points(slicer_name, polytope) == {(2.0, 3.0), (2.0, 4.0)}
