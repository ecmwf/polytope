# TODO: do the quadtree slicer, but only build quadtree for bbox of polygon


from copy import copy

from ..datacube.transformations.datacube_cyclic.datacube_cyclic import (
    DatacubeAxisCyclic,
)
from .engine import Engine

use_rust = False
try:
    from polytope_feature.polytope_rs import QuadTree

    use_rust = True

except (ModuleNotFoundError, ImportError) as e:
    print(f"Failed to load Rust extension with error: {e}, falling back to Python implementation.")
    from ..datacube.quadtree.quad_tree import QuadTree


class OptimisedQuadTreeSlicer(Engine):
    def __init__(self, points):
        # here need to construct quadtree, which is specific to datacube
        # NOTE: should this be inside of the datacube instead that we create the quadtree?
        # TODO: maybe we create the quadtree as soon as we have an unstructured slicer type and return it
        # to the slicer somehow?
        # quad_tree = QuadTree()
        self.points = [tuple(point) for point in points]
        # self.find_points_in_bbox(points, polytope)
        # quad_tree.build_point_tree(points)
        # self.points = points
        # self.quad_tree = quad_tree

    def find_points_in_bbox(self, polytope):
        x_min, x_max = polytope.extents(polytope.axes()[0])[:2]
        y_min, y_max = polytope.extents(polytope.axes()[1])[:2]

        filtered = [
            (i, point)
            for i, point in enumerate(self.points)
            if x_min <= point[0] <= x_max and y_min <= point[1] <= y_max
        ]

        self.bbox_indexes, self.bbox_points = zip(*filtered) if filtered else ([], [])

    def build_local_quadtree(self, polytope):
        quad_tree = QuadTree()
        self.find_points_in_bbox(polytope)
        quad_tree.build_point_tree(self.bbox_points)
        self.quad_tree = quad_tree

    def extract_single(self, datacube, polytope):
        self.build_local_quadtree(polytope)
        # extract a single polygon
        if use_rust:
            polytope_points = [tuple(point) for point in polytope.points]
            polygon_points = self.quad_tree.query_polygon(self.bbox_points, 0, polytope_points)
        else:
            polygon_points = self.quad_tree.query_polygon(polytope)

        # for point in polygon_points:
        #     assert self.bbox_points[point] in self.bbox_points
        return polygon_points

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:
                self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
        del node["unsliced_polytopes"]

    def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
        lon_ax = datacube._axes["longitude"]

        # When the longitude axis is cyclic, split the polygon at the seam first.
        sub_polytopes = [polytope]
        if lon_ax.is_cyclic and len(datacube.nearest_search) == 0:
            for t in lon_ax.transformations:
                if isinstance(t, DatacubeAxisCyclic):
                    sub_polytopes = t.split_polytope_at_boundary(polytope, "longitude", lon_ax)
                    break

        # Query each sub-polytope.  We must capture (global_index, lat, lon) immediately
        # after each extract_single call, because build_local_quadtree overwrites
        # self.bbox_indexes and self.bbox_points on every invocation.
        seen = {}  # global_index -> (lat_val, lon_val)
        for sub_poly in sub_polytopes:
            local_points = self.extract_single(datacube, sub_poly)
            for value in local_points:
                if use_rust:
                    actual_index = self.bbox_indexes[value]
                    lat_val = self.bbox_points[value][0]
                    lon_val = self.bbox_points[value][1]
                else:
                    actual_index = self.bbox_indexes[value.index]
                    lat_val = value.item[0]
                    lon_val = value.item[1]
                if actual_index not in seen:
                    seen[actual_index] = (lat_val, lon_val)

        if len(seen) == 0:
            node.remove_branch()
        lat_ax = ax
        for actual_index, (lat_val, lon_val) in seen.items():
            child, _ = node.create_child(lat_ax, lat_val, [])
            grand_child, _ = child.create_child(lon_ax, lon_val, [])
            grand_child.indexes = [actual_index]
            grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            grand_child["unsliced_polytopes"].remove(polytope)
