import pytest

from polytope_feature.datacube.quad_tree import QuadNode
from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer
from polytope_feature.utility.slicing_tools import slice_in_two
from polytope_feature.polytope import Polytope
from polytope_feature.shapes import Box, ConvexPolytope


class TestQuadTreeSlicer:
    def setup_method(self, method):
        import pygribjump as gj

        self.options = {
            "axis_config": [
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}
                    ],
                },
            ],
            "compressed_axes_config": [
                "longitude",
                "latitude",
                "levtype",
                "step",
                "date",
                "domain",
                "expver",
                "param",
                "class",
                "stream",
                "type",
            ],
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
        }
        self.fdbdatacube = gj.GribJump()

    @pytest.mark.fdb
    def test_quad_tree_slicer(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        slicer.quad_tree.pprint()
        pass

    @pytest.mark.fdb
    def test_quad_tree_query_polygon(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["lat", "lon"], [1, 1], [20, 30]).polytope()[0]
        results = slicer.quad_tree.query_polygon(polytope)
        assert len(results) == 3
        assert (10, 10) in [node.item for node in results]
        assert (5, 10) in [node.item for node in results]
        assert (5, 20) in [node.item for node in results]
        points = [[10, 10], [80, 10], [-5, 5], [5, 50], [5, 10], [50, 10], [2, 10], [15, 15]]
        slicer = QuadTreeSlicer(points)
        polytope = ConvexPolytope(["lat", "lon"], [[-10, 1], [20, 1], [5, 20]])
        results = slicer.quad_tree.query_polygon(polytope)
        assert len(results) == 4
        assert (-5, 5) in [node.item for node in results]
        assert (5, 10) in [node.item for node in results]
        assert (10, 10) in [node.item for node in results]
        assert (2, 10) in [node.item for node in results]

    @pytest.mark.fdb
    def test_slice_in_two_vertically(self):
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        lower, upper = slice_in_two(polytope, 1, 0)
        assert lower.points == [[0, 0], [1.0, 0.0], [1.0, 2.0], [0, 2]]
        assert upper.points == [[1.0, 0.0], [2, 0], [2, 2], [1.0, 2.0]]

    @pytest.mark.fdb
    def test_slice_in_two_horizontally(self):
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        lower, upper = slice_in_two(polytope, 1, 1)
        assert lower.points == [[0, 0], [2, 0], [2.0, 1.0], [0.0, 1.0]]
        assert upper.points == [[2, 2], [0, 2], [0.0, 1.0], [2.0, 1.0]]

    @pytest.mark.fdb
    def test_quad_node_is_contained_in_box(self):
        node = QuadNode([1, 1], 0)
        polytope = Box(["lat", "lon"], [0, 0], [2, 2]).polytope()[0]
        assert node.is_contained_in(polytope)
        second_node = QuadNode([3, 3], 0)
        assert not second_node.is_contained_in(polytope)
        third_node = QuadNode([1, 0], 0)
        assert third_node.is_contained_in(polytope)

    @pytest.mark.fdb
    def test_quad_node_is_contained_in_triangle(self):
        node = QuadNode([1, 1], 0)
        polytope = ConvexPolytope(["lat", "lon"], [[0, 0], [1, 1], [2, 0]])
        assert node.is_contained_in(polytope)
        node = QuadNode([1, 0.5], 0)
        assert node.is_contained_in(polytope)
        second_node = QuadNode([3, 3], 0)
        assert not second_node.is_contained_in(polytope)
        third_node = QuadNode([1, 0], 0)
        assert third_node.is_contained_in(polytope)
        third_node = QuadNode([0.1, 0.5], 0)
        assert not third_node.is_contained_in(polytope)

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options={"latitude": "quadtree", "longitude": "quadtree"},
            point_cloud_options=points,
        )
        tree = self.API.engines["quadtree"].extract_single(self.API.datacube, polytope)
        # tree = self.API.slice(self.API.datacube, [polytope])
        # assert len(tree.leaves) == 3
        assert len(tree) == 3
        # tree.pprint()
        points = [[10, 10], [80, 10], [-5, 5], [5, 50], [5, 10], [50, 10], [2, 10], [15, 15]]
        polytope = ConvexPolytope(["latitude", "longitude"], [[-10, 1], [20, 1], [5, 20]])
        tree = self.API.engines["quadtree"].extract_single(self.API.datacube, polytope)
        # tree = self.API.slice(self.API.datacube, [polytope])
        # assert len(tree.leaves) == 4
        assert len(tree) == 4
        # tree.pprint()

    # @pytest.mark.skip("performance test")
    @pytest.mark.fdb
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
        time0 = time.time()
        polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options={"latitude": "quadtree", "longitude": "quadtree"},
            point_cloud_options=points,
        )
        print(time.time() - time0)
        time1 = time.time()
        tree = self.API.engines["quadtree"].extract_single(self.API.datacube, polytope)
        print(time.time() - time1)  # = 5.919436931610107
        # print(len(tree.leaves))  # = 55100
        print(len(tree))  # = 55100
        # NOTE: maybe for 2D qhull here, scipy is not the fastest
        # but use shewchuk's triangle algo: https://www.cs.cmu.edu/~quake/triangle.html?
