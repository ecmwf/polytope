import scipy

from ..shapes import ConvexPolytope
from .hullslicer import _find_intersects


def slice_in_two(polytope: ConvexPolytope, value, slice_axis_idx):
    # print(value)
    if polytope is None:
        return (None, None)
    else:
        assert len(polytope.points[0]) == 2

        x_lower, x_upper, _ = polytope.extents(polytope._axes[slice_axis_idx])

        intersects = _find_intersects(polytope, slice_axis_idx, value)

        if len(intersects) == 0:
            if x_upper <= value:
                # The vertical slicing line does not intersect the polygon, which is on the left of the line
                # So we keep the same polygon for now since it is unsliced
                left_polygon = polytope
                right_polygon = None
            if value < x_lower:
                left_polygon = None
                right_polygon = polytope
        else:
            left_points = [p for p in polytope.points if p[slice_axis_idx] <= value]
            right_points = [p for p in polytope.points if p[slice_axis_idx] >= value]
            left_points.extend(intersects)
            right_points.extend(intersects)
            # find left polygon
            try:
                hull = scipy.spatial.ConvexHull(left_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                if "less than" or "is flat" in str(e):
                    # NOTE: this happens when we slice a polygon that has a border which coincides with the quadrant
                    # line and we slice this additional border with the quadrant line again.
                    # This is not actually a polygon we want to consider so we ignore it
                    vertices = None

            if vertices is not None:
                left_polygon = ConvexPolytope(polytope._axes, [left_points[i] for i in vertices])
            else:
                left_polygon = None

            try:
                hull = scipy.spatial.ConvexHull(right_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                # NOTE: this happens when we slice a polygon that has a border which coincides with the quadrant
                # line and we slice this additional border with the quadrant line again.
                # This is not actually a polygon we want to consider so we ignore it
                if "less than" or "is flat" in str(e):
                    vertices = None

            if vertices is not None:
                right_polygon = ConvexPolytope(polytope._axes, [right_points[i] for i in vertices])
            else:
                right_polygon = None

        return (left_polygon, right_polygon)
