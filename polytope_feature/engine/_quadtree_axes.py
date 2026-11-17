from copy import copy

# The point cloud returned by Datacube.find_point_cloud() (see e.g.
# datacube/backends/xarray.py::find_point_cloud -> grid_latlon_points()) is always ordered
# (latitude, longitude). Request shapes (see shapes.py) may declare their axes - and
# therefore their per-point coordinates - in any order (e.g. ["longitude", "latitude"]), so
# the quadtree engines must always look axes up by name rather than assume a fixed position.
CANONICAL_AXES = ("latitude", "longitude")


def axis_permutation(axes):
    """Index of each canonical (latitude, longitude) axis within `axes`, so that per-point
    coordinates declared in `axes` order can be permuted into canonical point-cloud order."""
    axes = list(axes)
    return [axes.index(name) for name in CANONICAL_AXES]


def reorder_points(polytope):
    """Return this polytope's points as plain (lat, lon) tuples, regardless of the axis order
    the shape was originally declared with."""
    axes = list(polytope.axes())
    if axes == list(CANONICAL_AXES):
        return [tuple(pt) for pt in polytope.points]
    perm = axis_permutation(axes)
    return [tuple(pt[i] for i in perm) for pt in polytope.points]


def canonical_polytope(polytope):
    """Return a polytope whose axes and points are aligned in canonical (latitude, longitude)
    order, matching the point cloud's coordinate layout. A shallow copy is returned only when
    reordering is actually needed, so the caller's original shape (and its declared axis
    order) is never mutated in place."""
    if list(polytope.axes()) == list(CANONICAL_AXES):
        return polytope
    reordered = copy(polytope)
    reordered._axes = list(CANONICAL_AXES)
    reordered.points = reorder_points(polytope)
    return reordered
