import pytest

from polytope.datacube.quad_tree import QuadNode
from polytope.engine.quadtree_slicer import QuadTreeSlicer
from polytope.engine.slicing_tools import slice_in_two
from polytope.shapes import Box, ConvexPolytope


class TestQuadTreeSlicer:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        self.options = {
            "values": {"mapper": {"type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl"}
        self.datacube = FDBDatacube(self.config, axis_options=self.options)

    def test_quad_tree_slicer(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        slicer.quad_tree.pprint()
        pass

    def test_quad_tree_query_polygon(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["lat", "lon"], [1, 1], [20, 30]).polytope()[0]
        results = slicer.quad_tree.query_polygon(polytope)
        assert len(results) == 3
        assert (10, 10, 10, 10) in [node.rect for node in results]
        assert (5, 10, 5, 10) in [node.rect for node in results]
        assert (5, 20, 5, 20) in [node.rect for node in results]
        points = [[10, 10], [80, 10], [-5, 5], [5, 50], [5, 10], [50, 10], [2, 10], [15, 15]]
        slicer = QuadTreeSlicer(points)
        polytope = ConvexPolytope(["lat", "lon"], [[-10, 1], [20, 1], [5, 20]])
        results = slicer.quad_tree.query_polygon(polytope)
        assert len(results) == 4
        assert (-5, 5, -5, 5) in [node.rect for node in results]
        assert (5, 10, 5, 10) in [node.rect for node in results]
        assert (10, 10, 10, 10) in [node.rect for node in results]
        assert (2, 10, 2, 10) in [node.rect for node in results]

    def test_slice_in_two_vertically(self):
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        lower, upper = slice_in_two(polytope, 1, 0)
        assert lower.points == [[0, 0], [1.0, 0.0], [1.0, 2.0], [0, 2]]
        assert upper.points == [[1.0, 0.0], [2, 0], [2, 2], [1.0, 2.0]]

    def test_slice_in_two_horizontally(self):
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        lower, upper = slice_in_two(polytope, 1, 1)
        assert lower.points == [[0, 0], [2, 0], [2.0, 1.0], [0.0, 1.0]]
        assert upper.points == [[2, 2], [0, 2], [0.0, 1.0], [2.0, 1.0]]

    def test_quad_node_is_contained_in_box(self):
        node = QuadNode(1, [1, 1, 1, 1], 0)
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        assert node.is_contained_in(polytope)
        second_node = QuadNode(1, [3, 3, 3, 3], 0)
        assert not second_node.is_contained_in(polytope)
        third_node = QuadNode(1, [1, 0, 1, 0], 0)
        assert third_node.is_contained_in(polytope)

    def test_quad_node_is_contained_in_triangle(self):
        node = QuadNode(1, [1, 1, 1, 1], 0)
        polytope = ConvexPolytope(["lat", "lon"], [[0, 0], [1, 1], [2, 0]])
        assert node.is_contained_in(polytope)
        node = QuadNode(1, [1, 0.5, 1, 0.5], 0)
        assert node.is_contained_in(polytope)
        second_node = QuadNode(1, [3, 3, 3, 3], 0)
        assert not second_node.is_contained_in(polytope)
        third_node = QuadNode(1, [1, 0, 1, 0], 0)
        assert third_node.is_contained_in(polytope)
        third_node = QuadNode(1, [0.1, 0.5, 0.1, 0.5], 0)
        assert not third_node.is_contained_in(polytope)

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
        tree = slicer.extract(self.datacube, [polytope])
        assert len(tree.leaves) == 3
        tree.pprint()
        points = [[10, 10], [80, 10], [-5, 5], [5, 50], [5, 10], [50, 10], [2, 10], [15, 15]]
        slicer = QuadTreeSlicer(points)
        polytope = ConvexPolytope(["latitude", "longitude"], [[-10, 1], [20, 1], [5, 20]])
        tree = slicer.extract(self.datacube, [polytope])
        assert len(tree.leaves) == 4
        tree.pprint()

    @pytest.mark.skip("performance test")
    def test_large_scale_extraction(self):
        import time

        import numpy as np

        x = np.linspace(0, 100, 1000)
        y = np.linspace(0, 100, 1000)
        # create the mesh based on these arrays
        X, Y = np.meshgrid(x, y)
        X = X.reshape((np.prod(X.shape),))
        Y = Y.reshape((np.prod(Y.shape),))
        coords = zip(X, Y)
        points = [list(coord) for coord in coords]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
        time1 = time.time()
        tree = slicer.extract(self.datacube, [polytope])
        print(time.time() - time1)  # = 5.919436931610107
        print(len(tree.leaves))  # = 55100
        # NOTE: maybe for 2D qhull here, scipy is not the fastest
        # but use shewchuk's triangle algo: https://www.cs.cmu.edu/~quake/triangle.html?
