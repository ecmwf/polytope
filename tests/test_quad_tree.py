from polytope.engine.quadtree_slicer import QuadTreeSlicer


class TestQuadTreeSlicer:
    def setup_method(self, method):
        pass

    def test_quad_tree_slicer(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        slicer.quad_tree.pprint()
