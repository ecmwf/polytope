import math

import scipy
import scipy.spatial

from ..shapes import ConvexPolytope


def lerp(a, b, value):
    intersect = [b + (a - b) * value for a, b in zip(a, b)]
    return intersect


def nearest_pt(pts_list, pt, k=1):
    """Return the k nearest points from pts_list to pt.

    pts_list is a list of items like [lat_values, lon_values]; we expand
    each into all combinations (lat, lon) and compute Euclidean distance
    to `pt`. If k==1 a single tuple is returned, otherwise a list of tuples
    ordered by increasing distance is returned.
    """
    new_pts_list = []
    for potential_pt in pts_list:
        for first_val in potential_pt[0]:
            for second_val in potential_pt[1]:
                new_pts_list.append((first_val, second_val))

    if not new_pts_list:
        return [] if k != 1 else None

    # compute distances
    dist_pts = [(l2_norm(p, pt), p) for p in new_pts_list]
    dist_pts.sort(key=lambda x: x[0])
    best = [p for _, p in dist_pts[:k]]
    return best


def l2_norm(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0]) * (pt1[0] - pt2[0]) + (pt1[1] - pt2[1]) * (pt1[1] - pt2[1]))


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


def slice_in_two(polytope, value, slice_axis_idx):
    """Split a 2-D ConvexPolytope along a vertical line at *value* on *slice_axis_idx*.

    Returns a (left_polygon, right_polygon) pair; either half may be None when the
    polygon lies entirely on one side of the cut.
    """
    if polytope is None:
        return (None, None)

    assert len(polytope.points[0]) == 2

    x_lower, x_upper, _ = polytope.extents(polytope._axes[slice_axis_idx])

    intersects = _find_intersects(polytope, slice_axis_idx, value)

    if len(intersects) == 0:
        if x_upper <= value:
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

        try:
            hull = scipy.spatial.ConvexHull(left_points)
            vertices = hull.vertices
        except scipy.spatial.qhull.QhullError as e:
            if "less than" or "is flat" in str(e):
                vertices = None

        left_polygon = (
            ConvexPolytope(polytope._axes, [left_points[i] for i in vertices], tag=polytope.tag)
            if vertices is not None
            else None
        )

        try:
            hull = scipy.spatial.ConvexHull(right_points)
            vertices = hull.vertices
        except scipy.spatial.qhull.QhullError as e:
            if "less than" or "is flat" in str(e):
                vertices = None

        right_polygon = (
            ConvexPolytope(polytope._axes, [right_points[i] for i in vertices], tag=polytope.tag)
            if vertices is not None
            else None
        )

    return (left_polygon, right_polygon)
