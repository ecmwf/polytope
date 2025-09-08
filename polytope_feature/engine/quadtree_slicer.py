from copy import copy

from .engine import Engine

use_rust = False
try:
    # from polytope_feature.quadtree import QuadTree
    from polytope_feature.polytope_rs import QuadTree

    use_rust = True
except (ModuleNotFoundError, ImportError):
    print("Failed to load Rust extension, falling back to Python implementation.")
    from ..datacube.quadtree.quad_tree import QuadTree


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # here need to construct quadtree, which is specific to datacube
        # NOTE: should this be inside of the datacube instead that we create the quadtree?
        # TODO: maybe we create the quadtree as soon as we have an unstructured slicer type and return it
        # to the slicer somehow?
        quad_tree = QuadTree()
        points = [tuple(point) for point in points]
        quad_tree.build_point_tree(points)
        self.points = points
        self.quad_tree = quad_tree

    def extract_single(self, datacube, polytope):
        # extract a single polygon
        if use_rust:
            polytope_points = [tuple(point) for point in polytope.points]
            polygon_points = self.quad_tree.query_polygon(self.points, 0, polytope_points)
        else:
            polygon_points = self.quad_tree.query_polygon(polytope)
        return polygon_points

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:
                self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
        del node["unsliced_polytopes"]

    def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
        extracted_points = self.extract_single(datacube, polytope)
        if len(extracted_points) == 0:
            node.remove_branch()
        lat_ax = ax
        lon_ax = datacube._axes["longitude"]
        for value in extracted_points:
            # convert to float for slicing
            if use_rust:
                lat_val = self.points[value][0]
                lon_val = self.points[value][1]
            else:
                lat_val = value.item[0]
                lon_val = value.item[1]
            # store the native type
            (child, _) = node.create_child(lat_ax, lat_val, [])
            (grand_child, _) = child.create_child(lon_ax, lon_val, [])
            # NOTE: the index of the point is stashed in the branches' result
            if use_rust:
                grand_child.indexes = [value]
            else:
                grand_child.indexes = [value.index]
            grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            grand_child["unsliced_polytopes"].remove(polytope)
