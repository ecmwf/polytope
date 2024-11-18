import math
import sys

import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.datacube.tensor_index_tree import TensorIndexTree
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import (
    Box,
    ConvexPolytope,
    Disk,
    PathSegment,
    Polygon,
    Select,
    Span,
    Union,
)


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129),
            dims=("date", "step", "level"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
            },
        )
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        options = {"compressed_axes_config": ["date", "step", "level"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    # Testing different shapes

    def test_2D_box(self):
        request = Request(Box(["step", "level"], [3, 10], [6, 11]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_2D_box_union_disjoint_boxes(self):
        box1 = Box(["step", "level"], [3, 10], [6, 11])
        box2 = Box(["step", "level"], [7, 15], [12, 17])
        request = Request(Union(["step", "level"], box1, box2), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 2

    def test_2D_box_union_overlapping_boxes(self):
        box1 = Box(["step", "level"], [3, 9], [6, 11])
        box2 = Box(["step", "level"], [6, 10], [12, 17])
        request = Request(Union(["step", "level"], box1, box2), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 2

    def test_point(self):
        request = Request(Select("date", ["2000-01-03"]), Select("level", [100]), Select("step", [3]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_segment(self):
        request = Request(Span("level", 10, 11), Select("date", ["2000-01-01"]), Select("step", [9]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["level"] == (10, 11)

    def test_union_line_point(self):
        seg1 = Span("step", 4.3, 6.2)
        pt1 = Select("step", [6.20001])
        request = Request(Union(["step"], seg1, pt1), Select("date", ["2000-01-01"]), Select("level", [100]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_union_boxes_intersect_one_point(self):
        box1 = Box(["step", "level"], [3, 10], [6, 11])
        box2 = Box(["step", "level"], [6, 11], [12, 17])
        request = Request(Union(["step", "level"], box1, box2), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 2

    def test_mix_existing_nonexisting_data(self):
        request = Request(Select("date", ["2000-01-03", "2000-01-04"]), Select("level", [100]), Select("step", [3]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_disk(self):
        request = Request(Disk(["level", "step"], [6, 6], [3, 3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 3
        assert len(result.leaves[0].values) == 1
        assert len(result.leaves[1].values) == 7
        assert len(result.leaves[2].values) == 1
        assert np.size(result.leaves[0].result[1]) == 1
        assert np.size(result.leaves[1].result[1]) == 7
        assert np.size(result.leaves[2].result[1]) == 1

    def test_concave_polygon(self):
        # TODO: fix the overlapping branches?
        points = [[1, 0], [3, 0], [2, 3], [3, 6], [1, 6]]
        request = Request(Polygon(["level", "step"], points), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        self.xarraydatacube.get(result)
        # result.pprint()
        assert len(result.leaves) == 8

    def test_polytope(self):
        points = [[0, 1], [3, 1], [3, 2], [0, 2]]
        request = Request(ConvexPolytope(["step", "level"], points), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        self.xarraydatacube.get(result)
        assert len(result.leaves) == 2
        for leaf in result.leaves:
            assert len(leaf.values) == 2
            assert np.size(leaf.result[1]) == 2

    # Testing empty shapes

    def test_union_empty_lines(self):
        # Slices non-existing step data
        seg1 = Span("step", 4, 5)
        seg2 = Span("step", 10, 11)
        request = Request(Union(["step"], seg1, seg2), Select("date", ["2000-01-01"]), Select("level", [100]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_empty_box_no_level(self):
        # Slices non-existing level data
        request = Request(Box(["step", "level"], [3, 10.5], [7, 10.99]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_empty_box_no_level_step(self):
        # Slices non-existing level and step data
        request = Request(Box(["step", "level"], [4, 10.5], [5, 10.99]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_empty_box_no_step(self):
        # Slices non-existing step and level data
        request = Request(Box(["step", "level"], [4, 10], [5, 10.49]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_empty_box_floating_steps(self):
        # Slices through no step data and float type level data
        request = Request(Box(["step", "level"], [4.1, 10.3], [5.7, 11.8]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_empty_box_no_step_level_float(self):
        # Slices empty step and level box
        request = Request(Box(["step", "level"], [4.1, 10.3], [5.7, 10.8]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_empty_no_step_unordered(self):
        # Slice empty box because no step is available
        request = Request(Box(["level", "step"], [10, 4], [10, 5]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_nonexisting_date(self):
        # Slices non-existing date data
        request = Request(Select("date", ["2000-01-04"]), Select("level", [100]), Select("step", [3]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_two_nonexisting_close_points(self):
        # Slices two close points neither of which are available in the datacube
        pt1 = Select("step", [2.99])
        pt2 = Select("step", [3.001])
        request = Request(Union(["step"], pt1, pt2), Select("level", [100]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_union_two_nonexisting_points(self):
        # Slices two close points neither of which are available in the datacube.
        # However if we round these points, we get points in the datacube
        pt1 = Select("step", [6.99])
        pt2 = Select("step", [3.001])
        request = Request(Union(["step"], pt1, pt2), Select("level", [100]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_two_close_points_no_level(self):
        # Slices non-existing step points and non-existing level
        pt1 = Select("step", [2.99])
        pt2 = Select("step", [3.001])
        request = Request(Union(["step"], pt1, pt2), Select("level", [100.1]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_nonexisting_point_float_level(self):
        # Slices non-existing level data
        request = Request(Select("step", [3]), Select("level", [99.1]), Select("date", ["2000-01-02"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_nonexisting_segment(self):
        # Slices non-existing step data
        request = Request(Span("step", 3.2, 3.23), Select("level", [99]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    # Testing edge cases

    def test_flat_box(self):
        # Should slice through a line in the step direction
        request = Request(Box(["step", "level"], [4, 10], [7, 10]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_box(self):
        # Should slice a line in the level direction
        request = Request(Box(["level", "step"], [3, 3], [6, 3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_swept_concave_polygon(self):
        # Tests what happens when we slice a concave shape which is swept across a path and see if concavity is lost
        points = [(1, 0), (3, 0), (3, 6), (2, 6), (2, 3), (1, 3)]
        concave_polygon = Polygon(["level", "step"], points)
        swept_poly = PathSegment(["level", "step"], concave_polygon, [0, 0], [1, 3])
        request = Request(swept_poly, Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        self.xarraydatacube.get(result)
        assert len(result.leaves) == 12

    # Testing special properties

    def test_intersection_point_disk_polygon(self):
        # should include point at level 1 and step 3, which is where the ellipse intersects its circumscribing polygon

        r1 = math.cos(math.pi / 12) * (8 - 4 * math.sqrt(3)) + sys.float_info.epsilon
        # note that we need a small perturbation to make up for rounding errors
        r2 = 3 * math.cos(math.pi / 12) * (math.sqrt(3) - 2) * (8 - 4 * math.sqrt(3)) / (4 * math.sqrt(3) - 7)
        request = Request(Disk(["level", "step"], [0, 0], [r1, r2]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        paths = [r.flatten().values() for r in result.leaves]
        assert ((pd.Timestamp("2000-01-01 00:00:00"),), (3,), (1,)) in paths

    def test_duplicate_values_select(self):
        request = Request(Select("step", [3, 3]), Select("level", [1]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()["step"]
        assert len(path) == 1
