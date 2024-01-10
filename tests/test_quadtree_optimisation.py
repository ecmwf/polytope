from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.quadtree_slicer import QuadTreeSlicer
from polytope.shapes import Box


class TestQuadTreeSlicer:
    def setup_method(self, method):
        self.options = {
            "values": {
                "transformation": {"mapper": {"type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}}
            },
            "date": {"transformation": {"merge": {"with": "time", "linkers": ["T", "00"]}}},
            "step": {"transformation": {"type_change": "int"}},
            "number": {"transformation": {"type_change": "int"}},
            "longitude": {"transformation": {"cyclic": [0, 360]}},
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl", "step": 0}
        self.datacube = FDBDatacube(self.config, axis_options=self.options)

    def test_quad_tree_slicer(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        slicer.quad_tree.pprint()
        pass

    def test_quad_tree_query_polygon(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["lat", "lon"], [0, 0], [90, 45]).polytope()[0]
        results = slicer.quad_tree.query_polygon(polytope)
        assert len(results) == 5
        assert (10, 10, 10, 10) in [node.rect for node in results]
        assert (5, 10, 5, 10) in [node.rect for node in results]
        assert (5, 20, 5, 20) in [node.rect for node in results]
        assert (80, 10, 80, 10) in [node.rect for node in results]
        assert (50, 10, 50, 10) in [node.rect for node in results]
