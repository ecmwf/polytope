import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope_feature.datacube.tensor_index_tree import TensorIndexTree
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import (
    Box,
    Disk,
    Ellipsoid,
    Path,
    PathSegment,
    Polygon,
    Select,
    Span,
    Union,
)
from polytope_feature.utility.exceptions import (
    AxisOverdefinedError,
    AxisUnderdefinedError,
)


class TestSlicing4DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 7, 129, 100),
            dims=("date", "step", "level", "lat"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15, 18],
                "level": range(1, 130),
                "lat": np.around(np.arange(0.0, 10.0, 0.1), 15),
            },
        )
        self.slicer = HullSlicer()
        options = {"compressed_axes_config": ["date", "step", "level", "lat"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    # Testing different shapes

    def test_3D_box(self):
        request = Request(Box(["step", "level", "lat"], [3, 10, 5.0], [6, 11, 6.0]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_4D_box(self):
        request = Request(Box(["step", "level", "lat", "date"], [3, 10, 5.0, "2000-01-01"], [6, 11, 6.0, "2000-01-02"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_circle_int(self):
        request = Request(
            Disk(["step", "level"], [9, 10], [6, 6]), Select("date", ["2000-01-01"]), Select("lat", [5.2])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 37

    def test_circles_barely_touching_int(self):
        disk1 = Disk(["step", "level"], [6, 10], [5.9, 6])
        disk2 = Disk(["step", "level"], [15, 10], [2.9, 3])
        request = Request(Union(["step", "level"], disk1, disk2), Select("date", ["2000-01-01"]), Select("lat", [5.1]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 45

    def test_circles_intersecting_float(self):
        disk1 = Disk(["step", "lat"], [6, 4.0], [6.99, 0.1])
        disk2 = Disk(["step", "lat"], [15, 2.0], [4.99, 0.3])
        request = Request(Union(["step", "lat"], disk1, disk2), Select("date", ["2000-01-01"]), Select("level", [10]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 24

    def test_circles_touching_float(self):
        disk1 = Disk(["step", "lat"], [6, 4.0], [3, 1.9])
        disk2 = Disk(["step", "lat"], [15, 2.0], [3, 2.1])
        request = Request(Union(["step", "lat"], disk1, disk2), Select("date", ["2000-01-01"]), Select("level", [10]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 101

    def test_pathsegment_swept_2D_box(self):
        box1 = Box(["step", "level"], [3, 0], [6, 1])
        request = Request(
            PathSegment(["step", "level"], box1, [3, 1], [6, 2]), Select("lat", [4.0]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 7

    def test_pathsegment_swept_2D_box_bis(self):
        # Had a floating point problem because of the latitude
        box1 = Box(["step", "level"], [3, 3], [6, 5])
        request = Request(
            PathSegment(["step", "level"], box1, [3, 3], [6, 6]), Select("lat", [4.1]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 12

    def test_pathsegment_swept_circle(self):
        circ1 = Disk(["step", "level"], [6, 3], [3, 2])
        request = Request(
            PathSegment(["step", "level"], circ1, [3, 3], [6, 6]), Select("lat", [5.5]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 14

    def test_path_swept_box_2_points(self):
        box1 = Box(["step", "level"], [3, 3], [6, 5])
        request = Request(
            Path(["step", "level"], box1, [3, 3], [6, 6]), Select("lat", [4.3]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 12

    def test_path_swept_box_3_points(self):
        box1 = Box(["step", "level"], [3, 3], [6, 5])
        request = Request(
            Path(["step", "level"], box1, [3, 3], [6, 6], [9, 9]), Select("lat", [4.3]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 18

    def test_polygon_other_than_triangle(self):
        polygon = Polygon(["step", "level"], [[3, 3], [3, 5], [6, 5], [6, 7]])
        request = Request(polygon, Select("lat", [4.3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 6

    def test_ellipsoid(self):
        ellipsoid = Ellipsoid(["step", "level", "lat"], [6, 3, 2.1], [3, 1, 0.1])
        request = Request(ellipsoid, Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 5
        assert len(result.leaves[2].values) == 3
        assert np.size(result.leaves[2].result[1]) == 3
        for i in range(len(result.leaves)):
            if i != 2:
                assert len(result.leaves[i].values) == 1
                assert np.size(result.leaves[i].result[1]) == 1

    # Testing empty shapes

    def test_empty_circle(self):
        # Slices a circle with no data inside
        request = Request(
            Disk(["step", "level"], [5, 3.4], [0.5, 0.2]), Select("date", ["2000-01-01"]), Select("lat", [5.1])
        )
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_float_box(self):
        # Slices a box with no data inside
        request = Request(
            Box(["step", "lat"], [10.1, 1.01], [10.3, 1.04]), Select("date", ["2000-01-01"]), Select("level", [10])
        )
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_path_empty_box(self):
        # Slices the path of a box with no data inside, but gives data because the box is swept over a datacube value
        box1 = Box(["step", "level"], [2.4, 3.1], [2.5, 3.4])
        request = Request(
            PathSegment(["step", "level"], box1, [3, 3], [6, 6]), Select("lat", [4.0]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_path_empty_box_empty(self):
        # Slices path of an empty box which isn't swept over a datacube point
        box1 = Box(["step", "level"], [2.4, 3.1], [2.5, 3.4])
        request = Request(
            PathSegment(["step", "level"], box1, [1.1, 3.3], [2.7, 3.6]),
            Select("lat", [4.0]),
            Select("date", ["2000-01-01"]),
        )
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_ellipsoid_empty(self):
        # Slices an empty ellipsoid which doesn't have any step value
        ellipsoid = Ellipsoid(["step", "level", "lat"], [5, 3, 2.1], [0, 0, 0])
        request = Request(ellipsoid, Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    # Testing special properties

    def test_span_bounds(self):
        # Tests that span also works in reverse order
        request = Request(
            Span("level", 100, 98), Select("step", [3]), Select("lat", [5.5]), Select("date", ["2000-01-01"])
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["level"] == (98, 99, 100)

    # Testing edge cases

    def test_ellipsoid_one_point(self):
        # Slices through a point (center of the ellipsoid)
        ellipsoid = Ellipsoid(["step", "level", "lat"], [6, 3, 2.1], [0, 0, 0])
        request = Request(ellipsoid, Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert not result.leaves[0].axis == TensorIndexTree.root

    def test_flat_box_level(self):
        # Slices a line in the step direction
        request = Request(Select("lat", [6]), Box(["level", "step"], [3, 3], [3, 9]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_flat_box_step(self):
        # Slices a line in the level direction
        request = Request(Select("lat", [6]), Box(["level", "step"], [3, 3], [7, 3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    def test_flat_disk_nonexisting(self):
        # Slices an empty disk because there is no step level
        request = Request(Disk(["level", "step"], [4, 5], [4, 0]), Select("lat", [6]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_flat_disk_line(self):
        # Slices a line in the level direction
        request = Request(Disk(["level", "step"], [4, 6], [4, 0]), Select("lat", [6]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 8

    def test_flat_disk_line_step(self):
        # Slices a line in the step direction
        request = Request(Disk(["level", "step"], [4, 6], [0, 3]), Select("lat", [6]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 3

    def test_flat_disk_empty(self):
        # Slices an empty disk because there is no step
        request = Request(Disk(["level", "step"], [4, 5], [0, 0.5]), Select("lat", [6]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_disk_point(self):
        # Slices a point because the origin of the disk is a datacube point
        request = Request(Disk(["level", "step"], [4, 6], [0, 0]), Select("lat", [6]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert not result.leaves[0].axis == TensorIndexTree.root

    def test_empty_disk(self):
        # Slices an empty object because the origin of the disk is not a datacube point
        request = Request(Disk(["level", "step"], [4, 5], [0, 0]), Select("lat", [6]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    def test_polygon_line(self):
        # Slices a line defined through the polygon shape
        polygon = Polygon(["step", "level"], [[3, 3], [3, 6], [3, 3], [3, 3]])
        request = Request(polygon, Select("lat", [4.3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 4

    def test_polygon_point(self):
        # Slices a point defined through the polygon object with several initial point entries.
        # Tests whether duplicate points are removed as they should
        polygon = Polygon(["step", "level"], [[3, 3], [3, 3], [3, 3], [3, 3]])
        request = Request(polygon, Select("lat", [4.3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        assert not result.leaves[0].axis == TensorIndexTree.root

    def test_polygon_empty(self):
        # Slices a point which isn't in the datacube (defined through the polygon shape)
        polygon = Polygon(["step", "level"], [[2, 3.1]])
        request = Request(polygon, Select("lat", [4.3]), Select("date", ["2000-01-01"]))
        result = self.API.retrieve(request)
        assert result.leaves[0].axis == TensorIndexTree.root

    # Test exceptions are returned correctly

    def test_axis_specified_twice(self):
        with pytest.raises(AxisOverdefinedError):
            request = Request(
                Box(["step", "level"], [3, 10], [6, 11]),
                Box(["step", "lat", "date"], [3, 5.0, "2000-01-01"], [6, 6.0, "2000-01-02"]),
            )
            result = self.API.retrieve(request)
            result.pprint()

    def test_not_all_axes_defined(self):
        with pytest.raises(AxisUnderdefinedError):
            request = Request(Box(["step", "level"], [3, 10], [6, 11]))
            result = self.API.retrieve(request)
            result.pprint()

    def test_not_all_axes_exist(self):
        with pytest.raises(KeyError):
            request = Request(Box(["weather", "level"], [3, 10], [6, 11]))
            result = self.API.retrieve(request)
            result.pprint()
