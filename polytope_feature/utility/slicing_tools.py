from copy import copy
from itertools import chain

import scipy
import scipy.spatial

from ..shapes import ConvexPolytope
from .geometry import lerp
from .list_tools import argmax, argmin


def slice_in_two(polytope: ConvexPolytope, value, slice_axis_idx):
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


def _find_intersects(polytope, slice_axis_idx, value):
    intersects = []
    # Find all points above and below slice axis
    above_slice = [p for p in polytope.points if p[slice_axis_idx] >= value]
    below_slice = [p for p in polytope.points if p[slice_axis_idx] <= value]

    # Get the intersection of every pair above and below, this will create excess interior points
    for a in above_slice:
        for b in below_slice:
            # edge is incident with slice plane, don't need these points
            if a[slice_axis_idx] == b[slice_axis_idx]:
                intersects.append(b)
                continue

            # Linearly interpolate all coordinates of two points (a,b) of the polytope
            interp_coeff = (value - b[slice_axis_idx]) / (a[slice_axis_idx] - b[slice_axis_idx])
            intersect = lerp(a, b, interp_coeff)
            intersects.append(intersect)
    return intersects


def _reduce_dimension(intersects, slice_axis_idx):
    temp_intersects = []
    for point in intersects:
        point = [p for i, p in enumerate(point) if i != slice_axis_idx]
        temp_intersects.append(point)
    return temp_intersects


def slice(polytope: ConvexPolytope, axis, value, slice_axis_idx):
    # TODO: maybe these functions should go in the slicing tools?
    if polytope.is_flat:
        if value in chain(*polytope.points):
            intersects = [[value]]
        else:
            return None
    else:
        intersects = _find_intersects(polytope, slice_axis_idx, value)

    if len(intersects) == 0:
        return None

    # Reduce dimension of intersection points, removing slice axis
    intersects = _reduce_dimension(intersects, slice_axis_idx)

    axes = copy(polytope._axes)
    axes.remove(axis)

    if len(intersects) < len(intersects[0]) + 1:
        return ConvexPolytope(axes, intersects)
    # Compute convex hull (removing interior points)
    if len(intersects[0]) == 0:
        return None
    elif len(intersects[0]) == 1:  # qhull doesn't like 1D, do it ourselves
        amin = argmin(intersects)
        amax = argmax(intersects)
        vertices = [amin, amax]
    else:
        try:
            hull = scipy.spatial.ConvexHull(intersects)
            vertices = hull.vertices

        except scipy.spatial.qhull.QhullError as e:
            if "less than" or "flat" in str(e):
                return ConvexPolytope(axes, intersects)
    # Sliced result is simply the convex hull
    return ConvexPolytope(axes, [intersects[i] for i in vertices])
