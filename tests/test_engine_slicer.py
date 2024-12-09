from polytope_feature.datacube.backends.mock import MockDatacube
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.shapes import Box, Polygon


class TestEngineSlicer:
    def setup_method(self, method):
        self.slicer = HullSlicer()

    def test_2D_box(self):
        datacube = MockDatacube({"x": 100, "y": 100})
        polytopes = Box(["x", "y"], lower_corner=[3, 3], upper_corner=[6, 6]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        result.pprint()
        assert len(result.leaves) == 4
        total_leaves = 0
        for leaf in result.leaves:
            total_leaves += len(leaf.values)
        assert total_leaves == 4 * 4

    def test_3D_box(self):
        datacube = MockDatacube({"x": 100, "y": 100, "z": 100})
        polytopes = Box(["x", "y", "z"], lower_corner=[3, 3, 3], upper_corner=[6, 6, 6]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        result.pprint()
        assert len(result.leaves) == 4 * 4
        total_leaves = 0
        for leaf in result.leaves:
            total_leaves += len(leaf.values)
        assert total_leaves == 4 * 4 * 4

    def test_4D_box(self):
        datacube = MockDatacube({"x": 100, "y": 100, "z": 100, "q": 100})
        polytopes = Box(["x", "y", "z", "q"], lower_corner=[3, 3, 3, 3], upper_corner=[6, 6, 6, 6]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        result.pprint()
        assert len(result.leaves) == 4 * 4 * 4
        total_leaves = 0
        for leaf in result.leaves:
            total_leaves += len(leaf.values)
        assert total_leaves == 4 * 4 * 4 * 4

    def test_triangle(self):
        datacube = MockDatacube({"x": 100, "y": 100})
        triangle = Polygon(["x", "y"], [[3, 3], [3, 6], [6, 3]]).polytope()
        result = self.slicer.extract(datacube, triangle)
        result.pprint()
        assert len(result.leaves) == 10
        # assert len(result.leaves) == 4
        # total_leaves = 0
        # for leaf in result.leaves:
        #     total_leaves += len(leaf.values)
        # assert total_leaves == 4 + 3 + 2 + 1

    def test_reusable(self):
        datacube = MockDatacube({"x": 100, "y": 100})
        polytopes = Polygon(["x", "y"], [[3, 3], [3, 6], [6, 3]]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        result.pprint()
        # assert len(result.leaves) == 4
        assert len(result.leaves) == 10
        polytopes = Box(["x", "y"], lower_corner=[3, 3], upper_corner=[6, 6]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        result.pprint()
        assert len(result.leaves) == 4

    def test_2D_box_get_function(self):
        datacube = MockDatacube({"x": 100, "y": 100})
        polytopes = Box(["x", "y"], lower_corner=[2, -2], upper_corner=[4, -1]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        datacube.get(result)
        result.pprint()

    def test_3D_box_get_function(self):
        datacube = MockDatacube({"x": 100, "y": 100, "z": 100})
        polytopes = Box(["x", "y", "z"], lower_corner=[3, 2, -2], upper_corner=[6, 2, -1]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        datacube.get(result)
        result.pprint()

    def test_3D_box_get_function2(self):
        datacube = MockDatacube({"x": 100, "y": 100, "z": 100})
        polytopes = Box(["x", "y", "z"], lower_corner=[3, 2, 1], upper_corner=[6, 2, 1]).polytope()
        result = self.slicer.extract(datacube, polytopes)
        datacube.get(result)
        result.pprint()
