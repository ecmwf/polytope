from copy import copy

import numpy as np

from ..datacube.datacube_axis import IntDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from .engine import Engine

use_rust = False
try:
    from polytope_feature.polytope_rs import extract_point_in_poly_bbox

    use_rust = True
except (ModuleNotFoundError, ImportError) as e:
    print(f"Failed to load Rust extension with error: {e}, falling back to Python implementation.")

    from shapely.geometry import Point
    from shapely.geometry.polygon import Polygon


class OptimisedPointInPolygonSlicer(Engine):
    resolves_axes_jointly = True

    def __init__(self, points):
        points = [tuple(point) for point in points]
        self.points = points
        self.bbox_points = []
        self._points = {point: i for i, point in enumerate(self.points)}
        self.points_array = np.asarray(self.points, dtype=np.float64).reshape(-1, 2)

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
            exists, child, _ = request.create_child(values_axis, idx, [])
            child.result = result

        return request

    def find_points_in_bbox(self, polytope):
        self.bbox_points = []
        bbox_x_range = polytope.extents(polytope.axes()[0])[:2]
        bbox_y_range = polytope.extents(polytope.axes()[1])[:2]
        for point in self.points:
            if bbox_x_range[0] <= point[0] <= bbox_x_range[1]:
                if bbox_y_range[0] <= point[1] <= bbox_y_range[1]:
                    self.bbox_points.append(point)

    def extract_single(self, datacube, polytope):
        # extract a single polygon

        # need to find points of the datacube contained within the polytope
        # We do this by intersecting the datacube point cloud quad tree with the polytope here

        # But here, we only consider the points in the bounding box of the polygon

        if polytope.method == "nearest":
            # Point shapes queried with method="nearest" carry raw query points rather than
            # a polygon, so a bbox pre-filter on the query point's own (degenerate) extents
            # would wrongly exclude nearby points. Resolve them with a brute-force
            # k-nearest search over the full point cloud instead, as the quadtree slicer does.
            found_points = []
            for query in polytope.points:
                found_points.extend(self._nearest_points(query, polytope.k))
            return found_points

        if len(polytope.points) == 1:
            # A single-vertex "polygon" is really a Point shape querying an exact
            # location, not a real polygon: a containment test needs at least 3
            # vertices, so resolve this as an exact coordinate match instead.
            self.find_points_in_bbox(polytope)
            qx, qy = polytope.points[0]
            return [p for p in self.bbox_points if p[0] == qx and p[1] == qy]

        if use_rust:
            polytope_points = [tuple(point) for point in polytope.points]
            found_points = extract_point_in_poly_bbox(self.points, polytope_points)
        else:
            self.find_points_in_bbox(polytope)

            found_points = []
            polygon = Polygon(polytope.points)
            for point in self.bbox_points:
                new_point = Point(point[0], point[1])
                if polygon.contains(new_point):
                    found_points.append(point)
        return found_points

    def _nearest_points(self, query, k):
        dists = np.sum((self.points_array - np.asarray(query)) ** 2, axis=1)
        k = min(k, len(dists))
        nearest = np.argpartition(dists, k - 1)[:k]
        nearest = nearest[np.argsort(dists[nearest])]
        return [self.points[i] for i in nearest.tolist()]

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
        extracted_points = self.extract_single(datacube, polytope)
        # TODO: add the sliced points as node to the tree and update the next_nodes
        if len(extracted_points) == 0:
            node.remove_branch()

        lat_ax = ax
        lon_ax = datacube._axes["longitude"]

        for point in extracted_points:
            # convert to float for slicing
            value = self.find_point_index(point)
            lat_val = point[0]
            lon_val = point[1]

            # store the native type
            exists, child, _ = node.create_child(lat_ax, lat_val, [])
            exists, grand_child, _ = child.create_child(lon_ax, lon_val, [])
            # NOTE: the index of the point is stashed in the branches' result
            grand_child.indexes = [value]
            grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            grand_child["unsliced_polytopes"].remove(polytope)
        # TODO: but now what happens to the second axis in the point cloud?? Do we create a second node for it??
