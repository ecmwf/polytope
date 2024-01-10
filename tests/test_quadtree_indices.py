from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.quadtree_slicer import QuadTreeSlicer
from polytope.shapes import Box, ConvexPolytope


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

    def test_quad_tree_slicer_extract(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
        tree = slicer.extract(self.datacube, [polytope])
        assert len(tree.leaves) == 3
        assert set([leaf.flatten()["values"] for leaf in tree.leaves]) == set([0, 3, 4])
        tree.pprint()
        points = [[10, 10], [80, 10], [-5, 5], [5, 50], [5, 10], [50, 10], [2, 10], [15, 15]]
        slicer = QuadTreeSlicer(points)
        polytope = ConvexPolytope(["latitude", "longitude"], [[-10, 1], [20, 1], [5, 20]])
        tree = slicer.extract(self.datacube, [polytope])
        assert len(tree.leaves) == 4
        assert set([leaf.flatten()["values"] for leaf in tree.leaves]) == set([0, 2, 4, 6])
        tree.pprint()
