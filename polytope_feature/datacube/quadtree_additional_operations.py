from ..engine.hullslicer import slice
from ..engine.slicing_tools import slice_in_two
from quadtree import QuadTreeNode


def is_contained_in(point, polygon):
    # implement method to check if the node point is inside the polygon
    node_x, node_y = point

    sliced_vertical_polygon = slice(polygon, polygon._axes[0], node_x, 0)
    if sliced_vertical_polygon:
        lower_y, upper_y, idx = sliced_vertical_polygon.extents(polygon._axes[1])
        if lower_y <= node_y <= upper_y:
            return True
    return False


def query_polygon(quadtree_points, node: QuadTreeNode, polygon, results=None):
    # intersect quad tree with a 2D polygon
    if results is None:
        results = set()

    # intersect the children with the polygon
    # TODO: here, we create None polygons... think about how to handle them
    if polygon is None:
        pass
    else:
        polygon_points = set([tuple(point) for point in polygon.points])
        # TODO: are these the right points which we are comparing, ie the points on the polygon
        # and the points on the rectangle quadrant?
        if polygon_points == node.quadrant_rectangle_points():
            for node in node.find_nodes_in():
                results.add(node)
        else:
            # TODO: DO NOT COPY THE CHILDREN INTO A LIST FROM RUST, INSTEAD IMPLEMENT A GETITEM EQUIVALENT AND ITER THROUGH THE RUST OBJECT DIRECTLY
            children = node.children
            if len(children) > 0:
                # first slice vertically
                left_polygon, right_polygon = slice_in_two(polygon, node.center[0], 0)

                # then slice horizontally
                # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

                q1_polygon, q2_polygon = slice_in_two(left_polygon, node.center[1], 1)
                q3_polygon, q4_polygon = slice_in_two(right_polygon, node.center[1], 1)

                # now query these 4 polygons further down the quadtree
                query_polygon(quadtree_points, children[0], q1_polygon, results)
                query_polygon(quadtree_points, children[1], q2_polygon, results)
                query_polygon(quadtree_points, children[2], q3_polygon, results)
                query_polygon(quadtree_points, children[3], q4_polygon, results)

            # if len(node) > 0:
            #     # first slice vertically
            #     left_polygon, right_polygon = slice_in_two(polygon, node.center[0], 0)

            #     # then slice horizontally
            #     # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

            #     q1_polygon, q2_polygon = slice_in_two(left_polygon, node.center[1], 1)
            #     q3_polygon, q4_polygon = slice_in_two(right_polygon, node.center[1], 1)

            #     # now query these 4 polygons further down the quadtree
            #     query_polygon(node[0], q1_polygon, results)
            #     query_polygon(node[1], q2_polygon, results)
            #     query_polygon(node[2], q3_polygon, results)
            #     query_polygon(node[3], q4_polygon, results)

            results.update((node, quadtree_points[node])
                           for node in node.points if is_contained_in(quadtree_points[node], polygon))

        return results
