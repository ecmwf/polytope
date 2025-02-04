from copy import copy

from ..datacube.quad_tree import QuadTree
from ..datacube.transformations.datacube_mappers import DatacubeMapper
from .engine import Engine


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # here need to construct quadtree, which is specific to datacube
        # NOTE: should this be inside of the datacube instead that we create the quadtree?
        super().__init__()
        quad_tree = QuadTree()
        quad_tree.build_point_tree(points)
        self.quad_tree = quad_tree
        self.second_axis = None

    def extract_single(self, datacube, polytope):
        # extract a single polygon

        # need to find points of the datacube contained within the polytope
        # We do this by intersecting the datacube point cloud quad tree with the polytope here
        polygon_points = self.quad_tree.query_polygon(polytope)
        return polygon_points

    def _build_branch(self, ax, node, datacube, next_nodes, api):
        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:
                # here, first check if the axis is an unsliceable axis and directly build node if it is

                # NOTE: here, we only have sliceable children, since the unsliceable children are handled by the
                # hullslicer engine?
                self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
        del node["unsliced_polytopes"]

    def break_up_polytope(self, datacube, polytope):
        new_polytopes = [polytope]
        for ax in polytope.axes():
            axis = datacube._axes[ax]
            if axis.is_cyclic:
                new_polytopes = axis.remap_polytopes(new_polytopes)
        return new_polytopes

    def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
        pre_sliced_polytopes = self.break_up_polytope(datacube, polytope)

        if not self.second_axis:
            for transform in ax.transformations:
                if isinstance(transform, DatacubeMapper):
                    self.second_axis = datacube._axes[transform.grid_axes[1]]

        node["unsliced_polytopes"].remove(polytope)

        for poly in pre_sliced_polytopes:
            node["unsliced_polytopes"].add(poly)

            extracted_points = self.extract_single(datacube, poly)
            # add the sliced points as node to the tree and update the next_nodes
            if len(extracted_points) == 0:
                node.remove_branch()

            for point in extracted_points:
                # convert to float for slicing
                value = point.index
                lat_val = point.item[0]
                lon_val = point.item[1]

                # store the native type
                (child, _) = node.create_child(ax, lat_val, [])
                (grand_child, _) = child.create_child(self.second_axis, lon_val, [])
                # NOTE: the index of the point is stashed in the branches' result
                grand_child.indexes = [value]
                grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
                grand_child["unsliced_polytopes"].remove(poly)
