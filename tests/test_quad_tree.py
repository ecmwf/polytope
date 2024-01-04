from polytope.engine.quadtree_slicer import (
    QuadNode,
    QuadTreeSlicer,
    slice_in_two_horizontally,
    slice_in_two_vertically,
)
from polytope.shapes import Box, ConvexPolytope


class TestQuadTreeSlicer:
    def setup_method(self, method):
        pass

    def test_quad_tree_slicer(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        slicer.quad_tree.pprint()
        pass

    def test_slice_in_two_vertically(self):
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        lower, upper = slice_in_two_vertically(polytope, 1)
        assert lower.points == [[0, 0], [1.0, 0.0], [1.0, 2.0], [0, 2]]
        assert upper.points == [[1.0, 0.0], [2, 0], [2, 2], [1.0, 2.0]]

    def test_slice_in_two_horizontally(self):
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        lower, upper = slice_in_two_horizontally(polytope, 1)
        assert lower.points == [[0, 0], [2, 0], [2.0, 1.0], [0.0, 1.0]]
        assert upper.points == [[2, 2], [0, 2], [0.0, 1.0], [2.0, 1.0]]

    def test_quad_node_is_contained_in_box(self):
        node = QuadNode(1, [1, 1, 1, 1])
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        assert node.is_contained_in(polytope)
        second_node = QuadNode(1, [3, 3, 3, 3])
        assert not second_node.is_contained_in(polytope)
        third_node = QuadNode(1, [1, 0, 1, 0])
        assert third_node.is_contained_in(polytope)

    def test_quad_node_is_contained_in_triangle(self):
        node = QuadNode(1, [1, 1, 1, 1])
        polytope = ConvexPolytope(["lat", "lon"], [[0, 0], [1, 1], [2, 0]])
        assert node.is_contained_in(polytope)
        node = QuadNode(1, [1, 0.5, 1, 0.5])
        assert node.is_contained_in(polytope)
        second_node = QuadNode(1, [3, 3, 3, 3])
        assert not second_node.is_contained_in(polytope)
        third_node = QuadNode(1, [1, 0, 1, 0])
        assert third_node.is_contained_in(polytope)
        third_node = QuadNode(1, [0.1, 0.5, 0.1, 0.5])
        assert not third_node.is_contained_in(polytope)
