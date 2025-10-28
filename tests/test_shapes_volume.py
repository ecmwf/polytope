from polytope_feature.shapes import ConvexPolytope, Point, Product


class TestShapeDimension:
    def setup_method(self, method):
        pass

    def test_point_dimension(self):
        point_1D = Point(["lat", "lon"], [[1, 1]])

        for shp in point_1D.polytope():
            assert isinstance(shp, Product)
            for polytope in shp._polytopes:
                assert len(polytope.axes()) == 1

        point_2D = Point(["lat", "lon"], [[1, 1]])
        point_2D.decompose_1D = False

        for shp in point_2D.polytope():
            assert isinstance(shp, ConvexPolytope)
            assert len(shp.axes()) == 2
