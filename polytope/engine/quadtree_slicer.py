from .engine import Engine
from ..shapes import ConvexPolytope
from itertools import chain
from .hullslicer import _find_intersects, slice
import scipy

"""

    QuadTree data structure

    comes from: https://github.com/mdrasmus/compbio/blob/master/rasmus/quadtree.py

"""


def normalize_rect(rect):
    x1, y1, x2, y2 = rect
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)


class QuadNode:
    def __init__(self, item, rect):
        self.item = item
        self.rect = rect

    def is_contained_in(self, polygon):
        # TODO: implement method to check if the node point is inside the polygon
        node_x = self.rect[0]
        node_y = self.rect[1]

        sliced_vertical_polygon = slice(polygon, polygon._axes[0], node_x, 0)
        if sliced_vertical_polygon:
            lower_y, upper_y, idx = sliced_vertical_polygon.extents(polygon._axes[1])
            if lower_y <= node_y <= upper_y:
                return True
        return False


class QuadTree:
    # TODO: do we need the max_depth?
    MAX = 4
    MAX_DEPTH = 20

    def __init__(self, x=0, y=0, size=[360, 180], depth=0):
        self.nodes = []
        self.children = []
        self.center = [x, y]
        self.size = size
        self.depth = depth

    def build_point_tree(self, points):
        for p in points:
            p_rect = (p[0], p[1], p[0], p[1])
            self.insert(p, p_rect)

    def pprint(self):
        if self.depth == 0:
            print("\n")
        if len(self.children) == 0:
            for n in self.nodes:
                print("\t" * (self.depth + 1) + "\u21b3" + str(n.rect[0]) + " , " + str(n.rect[1]))
        for child in self.children:
            print(
                "\t" * (self.depth + 1)
                + "\u21b3"
                + str(child.center[0] - child.size[0])
                + " , "
                + str(child.center[1] - child.size[1])
                + " , "
                + str(child.center[0] + child.size[0])
                + " , "
                + str(child.center[1] + child.size[1])
            )
            child.pprint()

    def insert(self, item, rect):
        rect = normalize_rect(rect)

        if len(self.children) == 0:
            node = QuadNode(item, rect)
            self.nodes.append(node)

            if len(self.nodes) > self.MAX and self.depth < self.MAX_DEPTH:
                self.split()
                return node
        else:
            return self.insert_into_children(item, rect)

    def insert_into_children(self, item, rect):
        # if rect spans center then insert here
        if (rect[0] <= self.center[0] and rect[2] > self.center[0]) and (
            rect[1] <= self.center[1] and rect[3] > self.center[1]
        ):
            node = QuadNode(item, rect)
            self.nodes.append(node)
            return node
        else:
            # try to insert into children
            if rect[0] <= self.center[0]:
                if rect[1] <= self.center[1]:
                    return self.children[0].insert(item, rect)
                if rect[3] > self.center[1]:
                    return self.children[1].insert(item, rect)
            if rect[2] > self.center[0]:
                if rect[1] <= self.center[1]:
                    return self.children[2].insert(item, rect)
                if rect[3] > self.center[1]:
                    return self.children[3].insert(item, rect)

    def split(self):
        self.children = [
            QuadTree(
                self.center[0] - self.size[0] / 2,
                self.center[1] - self.size[1] / 2,
                [s / 2 for s in self.size],
                self.depth + 1,
            ),
            QuadTree(
                self.center[0] - self.size[0] / 2,
                self.center[1] + self.size[1] / 2,
                [s / 2 for s in self.size],
                self.depth + 1,
            ),
            QuadTree(
                self.center[0] + self.size[0] / 2,
                self.center[1] - self.size[1] / 2,
                [s / 2 for s in self.size],
                self.depth + 1,
            ),
            QuadTree(
                self.center[0] + self.size[0] / 2,
                self.center[1] + self.size[1] / 2,
                [s / 2 for s in self.size],
                self.depth + 1,
            ),
        ]

        nodes = self.nodes
        self.nodes = []
        for node in nodes:
            self.insert_into_children(node.item, node.rect)

    # def query(self, rect, results=None):

    #     if results is None:
    #         rect = normalize_rect(rect)
    #         results = set()

    #     # search children
    #     if len(self.children) > 0:
    #         if rect[0] <= self.center[0]:
    #             if rect[1] <= self.center[1]:
    #                 self.children[0].query(rect, results)
    #             if rect[3] > self.center[1]:
    #                 self.children[1].query(rect, results)
    #         if rect[2] > self.center[0]:
    #             if rect[1] <= self.center[1]:
    #                 self.children[2].query(rect, results)
    #             if rect[3] > self.center[1]:
    #                 self.children[3].query(rect, results)

    #     # search node at this level
    #     for node in self.nodes:
    #         if (node.rect[2] > rect[0] and node.rect[0] <= rect[2] and
    #                 node.rect[3] > rect[1] and node.rect[1] <= rect[3]):
    #             results.add(node.item)

    #     return results

    # def get_size(self):
    #     size = 0
    #     for child in self.children:
    #         size += child.get_size()
    #     size += len(self.nodes)
    #     return size

    def query_polygon(self, polygon, results=None):
        # TODO: intersect quad tree with a 2D polygon
        if results is None:
            results = set()

        # intersect the children with the polygon
        # TODO: here, we create None polygons... think about how to handle them
        if polygon is None:
            pass
        else:
            left_polygon, right_polygon = slice_in_two_vertically(polygon, self.center[0])

            # TODO: now need to slice the left and right polygons each in two to have the 4 quadrant polygons
            q1_polygon, q2_polygon = slice_in_two_horizontally(left_polygon, self.center[1])
            q3_polygon, q4_polygon = slice_in_two_horizontally(right_polygon, self.center[1])

            # TODO: now query these 4 polygons further down the quadtree
            self.children[0].query_polygon(q1_polygon, results)
            self.children[1].query_polygon(q2_polygon, results)
            self.children[2].query_polygon(q3_polygon, results)
            self.children[3].query_polygon(q4_polygon, results)

            # x_lower, x_upper = polygon.extents(polygon._axes[0])
            # y_lower, y_upper = polygon.extents(polygon._axes[1])
            # if len(self.children) > 0:
            #     # TODO: do the intersection bit here
            #     if x_upper <= self.center[0]:
            #         # The vertical slicing line does not intersect the polygon, which is on the left of the line
            #         # So we keep the same polygon for now since it is unsliced
            #         left_polygon = polygon
            #         right_polygon = None
            #     if x_lower <= self.center[0] < x_upper:
            #         # TODO: need to slice polygon into left and right part
            #         pass
            #     if self.center[0] < x_lower:
            #         left_polygon = None
            #         right_polygon = polygon
            #     pass

            for node in self.nodes:
                if node.is_contained_in(polygon):
                    results.add(node)

            return results


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # TODO: here need to construct quadtree, which is specific to datacube
        quad_tree = QuadTree()
        quad_tree.build_point_tree(points)
        self.quad_tree = quad_tree

    # TODO: method to slice polygon against quadtree
    def extract(self, datacube, polytopes):
        # TODO: need to find the points to extract within the polytopes (polygons here in 2D)
        for polytope in polytopes:
            assert len(polytope._axes) == 2
            self.extract_single(datacube, polytope)

    def extract_single(self, datacube, polytope):
        # TODO: extract a single polygon

        # TODO: need to find points of the datacube contained within the polytope
        # We do this by intersecting the datacube point cloud quad tree with the polytope here
        polygon_points = self.quad_tree.query_polygon(polytope)
        return polygon_points


def slice_in_two_vertically(polytope: ConvexPolytope, value):
    if polytope is None:
        pass
    else:
        assert len(polytope.points[0]) == 2

        x_lower, x_upper, slice_axis_idx = polytope.extents(polytope._axes[0])

        slice_axis_idx = 0

        intersects = _find_intersects(polytope, slice_axis_idx, value)

        if len(intersects) == 0:
            if x_upper <= value:
                # The vertical slicing line does not intersect the polygon, which is on the left of the line
                # So we keep the same polygon for now since it is unsliced
                left_polygon = polytope
                right_polygon = None
            if value < x_lower:
                left_polygon = None
                right_polygon = polytope
        else:
            left_points = [p for p in polytope.points if p[0] <= value]
            right_points = [p for p in polytope.points if p[0] >= value]
            left_points.extend(intersects)
            right_points.extend(intersects)
            # find left polygon
            try:
                hull = scipy.spatial.ConvexHull(left_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                print(str(e))
                pass

            left_polygon = ConvexPolytope(polytope._axes, [left_points[i] for i in vertices])

            try:
                hull = scipy.spatial.ConvexHull(right_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                print(str(e))
                pass

            right_polygon = ConvexPolytope(polytope._axes, [right_points[i] for i in vertices])

        return (left_polygon, right_polygon)


def slice_in_two_horizontally(polytope: ConvexPolytope, value):
    if polytope is None:
        pass
    else:
        assert len(polytope.points[0]) == 2

        y_lower, y_upper, slice_axis_idx = polytope.extents(polytope._axes[1])

        slice_axis_idx = 1

        intersects = _find_intersects(polytope, slice_axis_idx, value)

        if len(intersects) == 0:
            if y_upper <= value:
                # The vertical slicing line does not intersect the polygon, which is on the left of the line
                # So we keep the same polygon for now since it is unsliced
                lower_polygon = polytope
                upper_polygon = None
            if value < y_lower:
                lower_polygon = None
                upper_polygon = polytope
        else:
            lower_points = [p for p in polytope.points if p[1] <= value]
            upper_points = [p for p in polytope.points if p[1] >= value]
            lower_points.extend(intersects)
            upper_points.extend(intersects)
            # find left polygon
            try:
                hull = scipy.spatial.ConvexHull(lower_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                print(str(e))
                pass

            lower_polygon = ConvexPolytope(polytope._axes, [lower_points[i] for i in vertices])

            try:
                hull = scipy.spatial.ConvexHull(upper_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                print(str(e))
                pass

            upper_polygon = ConvexPolytope(polytope._axes, [upper_points[i] for i in vertices])

        return (lower_polygon, upper_polygon)
