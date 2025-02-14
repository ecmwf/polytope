from copy import copy

from ..datacube.datacube_axis import IntDatacubeAxis
# from ..datacube.quad_tree import QuadTree
from quadtree import QuadTreeNode
from ..datacube.quadtree_additional_operations import query_polygon
from ..datacube.tensor_index_tree import TensorIndexTree
from .engine import Engine


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # here need to construct quadtree, which is specific to datacube
        # NOTE: should this be inside of the datacube instead that we create the quadtree?
        import time
        quad_tree = QuadTreeNode(0, 0)
        print("START BUILDING QUAD TREE")
        time0 = time.time()
        quad_tree.build_point_tree(points)
        self.points = points
        print("FINISH BUILDING QUAD TREE")
        print(time.time()-time0)
        self.quad_tree = quad_tree

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
            idx = point.index
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
        polygon_points = query_polygon(self.points, self.quad_tree, polytope)
        return polygon_points

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
            value = point.index
            lat_val = point.item[0]
            lon_val = point.item[1]
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


# from copy import copy

# from ..datacube.datacube_axis import IntDatacubeAxis
# from ..datacube.quad_tree import QuadTree
# from ..datacube.tensor_index_tree import TensorIndexTree
# from .engine import Engine


# class QuadTreeSlicer(Engine):
#     def __init__(self, points):
#         # here need to construct quadtree, which is specific to datacube
#         # NOTE: should this be inside of the datacube instead that we create the quadtree?
#         import time
#         quad_tree = QuadTree()
#         print("START BUILDING QUAD TREE")
#         time0 = time.time()
#         quad_tree.build_point_tree(points)
#         print("FINISH BUILDING QUAD TREE")
#         print(time.time()-time0)
#         self.quad_tree = quad_tree

#     # method to slice polygon against quadtree
#     def extract(self, datacube, polytopes):
#         # need to find the points to extract within the polytopes (polygons here in 2D)
#         request = TensorIndexTree()
#         extracted_points = []
#         for polytope in polytopes:
#             assert len(polytope._axes) == 2
#             extracted_points.extend(self.extract_single(datacube, polytope))

#         # what data format do we return extracted points as? Append those points to the index tree?

#         # NOTE: for now, we return the indices of the points in the point cloud, instead of lat/lon
#         for point in extracted_points:
#             # append each found leaf to the tree
#             idx = point.index
#             values_axis = IntDatacubeAxis()
#             values_axis.name = "values"
#             result = point.item
#             # TODO: make finding the axes objects nicer?
#             (child, _) = request.create_child(values_axis, idx, [])
#             child.result = result

#         return request

#     def extract_single(self, datacube, polytope):
#         # extract a single polygon

#         # need to find points of the datacube contained within the polytope
#         # We do this by intersecting the datacube point cloud quad tree with the polytope here
#         polygon_points = self.quad_tree.query_polygon(polytope)
#         return polygon_points

#     def _build_branch(self, ax, node, datacube, next_nodes, api):
#         for polytope in node["unsliced_polytopes"]:
#             if ax.name in polytope._axes:
#                 # here, first check if the axis is an unsliceable axis and directly build node if it is

#                 # NOTE: here, we only have sliceable children, since the unsliceable children are handled by the
#                 # hullslicer engine? IS THIS TRUE?
#                 self._build_sliceable_child(polytope, ax, node, datacube, next_nodes, api)
#                 # TODO: what does this function actually return and what should it return?
#                 # It just modifies the next_nodes?
#         del node["unsliced_polytopes"]

#     def _build_sliceable_child(self, polytope, ax, node, datacube, next_nodes, api):
#         extracted_points = self.extract_single(datacube, polytope)
#         # TODO: add the sliced points as node to the tree and update the next_nodes
#         if len(extracted_points) == 0:
#             node.remove_branch()

#         for point in extracted_points:
#             # convert to float for slicing
#             value = point.index
#             lat_val = point.item[0]
#             lon_val = point.item[1]
#             lat_ax = ax

#             # TODO: is there a nicer way to get this axis that does not depend on knowing
#             # the axis name in advance?
#             lon_ax = datacube._axes["longitude"]

#             # store the native type
#             (child, _) = node.create_child(lat_ax, lat_val, [])
#             (grand_child, _) = child.create_child(lon_ax, lon_val, [])
#             # NOTE: the index of the point is stashed in the branches' result
#             grand_child.indexes = [value]
#             grand_child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
#             grand_child["unsliced_polytopes"].remove(polytope)
#         # TODO: but now what happens to the second axis in the point cloud?? Do we create a second node for it??
