
try:
    from quadtree import QuadTree
except (ModuleNotFoundError, ImportError):
    print("Failed to load Rust extension.")

from ..engine.hullslicer import slice
from ..engine.slicing_tools import slice_in_two

# TODO: make this as methods of the python quadtree?


def is_contained_in(point, polygon):
    # implement method to check if the node point is inside the polygon
    node_x, node_y = point

    sliced_vertical_polygon = slice(polygon, polygon._axes[0], node_x, 0)
    if sliced_vertical_polygon:
        lower_y, upper_y, idx = sliced_vertical_polygon.extents(polygon._axes[1])
        if lower_y <= node_y <= upper_y:
            return True
    return False


# def query_polygon(quadtree_points, quadtree: QuadTree, node_idx, polygon, results=None):
#     # intersect quad tree with a 2D polygon
#     if results is None:
#         results = set()

#     # intersect the children with the polygon
#     # TODO: here, we create None polygons... think about how to handle them
#     if polygon is None:
#         return results
#     else:
#         polygon_points = {tuple(point) for point in polygon.points}
#         # TODO: are these the right points which we are comparing, ie the points on the polygon
#         # and the points on the rectangle quadrant?
#         if sorted(list(polygon_points)) == quadtree.quadrant_rectangle_points(node_idx):
#             results.update(quadtree.find_nodes_in(node_idx))
#         else:
#             children_idxs = quadtree.get_children_idxs(node_idx)
#             if len(children_idxs) > 0:
#                 # first slice vertically
#                 quadtree_center = quadtree.get_center(node_idx)
#                 left_polygon, right_polygon = slice_in_two(polygon, quadtree_center[0], 0)

#                 # then slice horizontally
#                 # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

#                 q1_polygon, q2_polygon = slice_in_two(left_polygon, quadtree_center[1], 1)
#                 q3_polygon, q4_polygon = slice_in_two(right_polygon, quadtree_center[1], 1)

#                 # now query these 4 polygons further down the quadtree
#                 query_polygon(quadtree_points, quadtree, children_idxs[0], q1_polygon, results)
#                 query_polygon(quadtree_points, quadtree, children_idxs[1], q2_polygon, results)
#                 query_polygon(quadtree_points, quadtree, children_idxs[2], q3_polygon, results)
#                 query_polygon(quadtree_points, quadtree, children_idxs[3], q4_polygon, results)

#             # TODO: try optimisation: take bbox of polygon and quickly remove the results that are not in bbox already
#             else:
#                 # print(quadtree.get_point_idxs(node_idx))
#                 # print(polygon.points)
#                 # print(len(children_idxs))
#                 results.update(
#                     node for node in quadtree.get_point_idxs(node_idx)
#                     if is_contained_in(quadtree_points[node], polygon)
#                 )
#         return results


def query_polygon(quadtree_points, quadtree, node_idx, polygon):
    results = set()
    _query_polygon(quadtree_points, quadtree, node_idx, polygon, results)
    return results


def _query_polygon(quadtree_points, quadtree: QuadTree, node_idx, polygon, results):
    # intersect quad tree with a 2D polygon
    # if results is None:
    #     results = set()

    # intersect the children with the polygon
    # TODO: here, we create None polygons... think about how to handle them
    if polygon is None:
        return results
    else:
        polygon_points = {tuple(point) for point in polygon.points}
        # TODO: are these the right points which we are comparing, ie the points on the polygon
        # and the points on the rectangle quadrant?
        if sorted(list(polygon_points)) == quadtree.quadrant_rectangle_points(node_idx):
            results.update(quadtree.find_nodes_in(node_idx))
        else:
            children_idxs = quadtree.get_children_idxs(node_idx)
            if len(children_idxs) > 0:
                # first slice vertically
                quadtree_center = quadtree.get_center(node_idx)
                left_polygon, right_polygon = slice_in_two(polygon, quadtree_center[0], 0)

                # then slice horizontally
                # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

                q1_polygon, q2_polygon = slice_in_two(left_polygon, quadtree_center[1], 1)
                q3_polygon, q4_polygon = slice_in_two(right_polygon, quadtree_center[1], 1)

                # now query these 4 polygons further down the quadtree
                _query_polygon(quadtree_points, quadtree, children_idxs[0], q1_polygon, results)
                _query_polygon(quadtree_points, quadtree, children_idxs[1], q2_polygon, results)
                _query_polygon(quadtree_points, quadtree, children_idxs[2], q3_polygon, results)
                _query_polygon(quadtree_points, quadtree, children_idxs[3], q4_polygon, results)

            # TODO: try optimisation: take bbox of polygon and quickly remove the results that are not in bbox already
            else:
                # print(quadtree.get_point_idxs(node_idx))
                # print(polygon.points)
                # print(len(children_idxs))
                results.update(
                    node
                    for node in quadtree.get_point_idxs(node_idx)
                    if is_contained_in(quadtree_points[node], polygon)
                )
        # return results
