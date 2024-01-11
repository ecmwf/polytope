from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.quadtree_slicer import QuadTreeSlicer
from polytope.engine.slicing_tools import visualise_slicing
from polytope.shapes import Box, ConvexPolytope
from polytope.datacube.quad_tree import QuadTree


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.options = {
            "values": {"mapper": {"type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl"}
        self.datacube = FDBDatacube(self.config, axis_options=self.options)

    def test_quad_tree_query_polygon(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        # polytope = Box(["lat", "lon"], [1, 1], [20, 30]).polytope()[0]
        polytope = ConvexPolytope(["lat", "lon"], [[1, 1], [1, 30], [20, 30], [20, 1]])
        slicer.quad_tree.query_polygon_visualised(polytope, points=points)
        # visualise_slicing(polytope, 10, 0)
