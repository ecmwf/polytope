from copy import copy

from ..datacube.datacube_axis import IntDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from ..datacube.transformations.datacube_cyclic.datacube_cyclic import (
    DatacubeAxisCyclic,
)
from .engine import Engine

use_rust = False
try:
    from polytope_feature.polytope_rs import extract_point_in_poly

    use_rust = True
except (ModuleNotFoundError, ImportError) as e:
    print(f"Failed to load Rust extension with error: {e}, falling back to Python implementation.")


def _convex_hull(points):
    """Return the vertices of the convex hull of *points* in CCW order.

    Uses a straightforward Graham-scan implementation.  *points* is a sequence
    of length-2 iterables (e.g. ``[[x0,y0], [x1,y1], ...]``).
    """
    pts = [tuple(p) for p in points]
    pts = sorted(set(pts))
    if len(pts) <= 1:
        return pts

    def _cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower = []
    for p in pts:
        while len(lower) >= 2 and _cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)

    upper = []
    for p in reversed(pts):
        while len(upper) >= 2 and _cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)

    # Concatenate, dropping the last point of each half (duplicates of endpoints).
    return lower[:-1] + upper[:-1]


def _point_in_convex_hull(point, hull):
    """Return True if *point* lies inside or on the boundary of the convex *hull*.

    *hull* must be a list of vertices in CCW order as returned by ``_convex_hull``.
    Uses the cross-product sign test: a point is inside a CCW convex polygon iff
    it is to the left of (or on) every directed edge.
    """
    n = len(hull)
    if n == 0:
        return False
    if n == 1:
        return point[0] == hull[0][0] and point[1] == hull[0][1]
    px, py = point[0], point[1]
    for i in range(n):
        ax, ay = hull[i]
        bx, by = hull[(i + 1) % n]
        # cross product of (b-a) x (p-a); negative → point is to the right → outside
        if (bx - ax) * (py - ay) - (by - ay) * (px - ax) < 0:
            return False
    return True


class PointInPolygonSlicer(Engine):
    def __init__(self, points):
        self.points = points
        self._points = {point: i for i, point in enumerate(self.points)}

    def find_point_index(self, point):
        index = self._points[point]
        return index

    # method to slice polygon against quadtree
    def extract(self, datacube, polytopes):
        # need to find the points to extract within the polytopes (polygons here in 2D)
        request = TensorIndexTree()
        extracted_points = []
        for polytope in polytopes:
            assert len(polytope._axes) == 2
            extracted_points.extend(self.extract_single(datacube, polytope))

        # what data format do we return extracted points as? Append those points to the index tree?

        # NOTE: for now, we return the indices of the points in the point cloud, instead of lat/lon
        for point in extracted_points:
            # append each found leaf to the tree
            idx = self.find_point_index(point)
            values_axis = IntDatacubeAxis()
            values_axis.name = "values"
            result = point.item
            # TODO: make finding the axes objects nicer?
            child, _ = request.create_child(values_axis, idx, [])
            child.result = result

        return request

    def extract_single(self, datacube, polytope):
        # extract a single polygon

        # need to find points of the datacube contained within the polytope
        # We do this by intersecting the datacube point cloud quad tree with the polytope here
        if use_rust:
            polytope_points = [tuple(point) for point in polytope.points]
            found_points = extract_point_in_poly(self.points, polytope_points)
        else:
            hull = _convex_hull(polytope.points)
            found_points = [p for p in self.points if _point_in_convex_hull(p, hull)]
        return found_points

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:
                # here, first check if the axis is an unsliceable axis and directly build node if it is

                # NOTE: here, we only have sliceable children, since the unsliceable children are handled by the
                # hullslicer engine? IS THIS TRUE?
                self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
                # TODO: what does this function actually return and what should it return?
                # It just modifies the next_nodes?
        del node["unsliced_polytopes"]

    def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
        lon_ax = datacube._axes["longitude"]

        # Split across the cyclic seam when needed.
        sub_polytopes = [polytope]
        if lon_ax.is_cyclic:
            for t in lon_ax.transformations:
                if isinstance(t, DatacubeAxisCyclic):
                    sub_polytopes = t.split_polytope_at_boundary(polytope, "longitude", lon_ax)
                    break

        # Gather unique points (dedup by (lat, lon) tuple).
        seen = {}  # (lat, lon) -> global index
        for sub_poly in sub_polytopes:
            for point in self.extract_single(datacube, sub_poly):
                key = (point[0], point[1])
                if key not in seen:
                    seen[key] = self.find_point_index(point)

        if len(seen) == 0:
            node.remove_branch()

        lat_ax = ax
        for (lat_val, lon_val), value in seen.items():
            child, _ = node.create_child(lat_ax, lat_val, [])
            grand_child, _ = child.create_child(lon_ax, lon_val, [])
            grand_child.indexes = [value]
            grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            grand_child["unsliced_polytopes"].remove(polytope)
