from .engine import Engine
from ..datacube.tensor_index_tree import TensorIndexTree
from ..datacube.datacube_axis import IntDatacubeAxis
from copy import copy


use_rust = False
try:
    from polytope_feature.polytope_rs import extract_point_in_poly

    use_rust = True
except (ModuleNotFoundError, ImportError):
    print("Failed to load Rust extension, falling back to Python implementation.")

    from shapely.geometry import Point
    from shapely.geometry.polygon import Polygon


class PointInPolygonSlicer(Engine):
    def __init__(self, points):
        self.points = points

    def find_point_index(self, point):
        index = self.points.index(point)
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
            (child, _) = request.create_child(values_axis, idx, [])
            child.result = result

        return request

    def extract_single(self, datacube, polytope):
        # extract a single polygon

        # need to find points of the datacube contained within the polytope
        # We do this by intersecting the datacube point cloud quad tree with the polytope here
        if use_rust:
            found_points = extract_point_in_poly(self.points, polytope)
        else:
            found_points = []
            for point in self.points:
                new_point = Point(point[0], point[1])
                polygon = Polygon(polytope.points)
                if polygon.contains(new_point):
                    found_points.append(point)
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
        extracted_points = self.extract_single(datacube, polytope)
        # TODO: add the sliced points as node to the tree and update the next_nodes
        if len(extracted_points) == 0:
            node.remove_branch()

        for point in extracted_points:
            # convert to float for slicing
            value = self.find_point_index(point)
            lat_val = point[0]
            lon_val = point[1]
            lat_ax = ax

            # TODO: is there a nicer way to get this axis that does not depend on knowing
            # the axis name in advance?
            lon_ax = datacube._axes["longitude"]

            # store the native type
            (child, _) = node.create_child(lat_ax, lat_val, [])
            (grand_child, _) = child.create_child(lon_ax, lon_val, [])
            # NOTE: the index of the point is stashed in the branches' result
            grand_child.indexes = [value]
            grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            grand_child["unsliced_polytopes"].remove(polytope)
        # TODO: but now what happens to the second axis in the point cloud?? Do we create a second node for it??
