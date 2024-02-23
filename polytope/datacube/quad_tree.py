from ..engine.hullslicer import slice
from ..engine.slicing_tools import slice_in_two

"""

    QuadTree data structure

    comes from: https://github.com/mdrasmus/compbio/blob/master/rasmus/quadtree.py

    is specific to 2D

"""


def normalize_rect(rect):
    x1, y1, x2, y2 = rect
    if x1 > x2:
        x1, x2 = x2, x1
    if y1 > y2:
        y1, y2 = y2, y1
    return (x1, y1, x2, y2)


class QuadNode:
    def __init__(self, item, rect, index):
        self.item = item
        self.rect = rect
        self.index = index

    def is_contained_in(self, polygon):
        # implement method to check if the node point is inside the polygon
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
    MAX = 3
    MAX_DEPTH = 20

    def __init__(self, x=0, y=0, size=[180, 90], depth=0):
        self.nodes = []
        self.children = []
        self.center = [x, y]
        self.size = size
        self.depth = depth
        # self.parent = self

    def quadrant_rectangle_points(self):
        return set(
            [
                (self.center[0] + (self.size[0]), self.center[1] + (self.size[1])),
                (self.center[0] + (self.size[0]), self.center[1] - (self.size[1])),
                (self.center[0] - (self.size[0]), self.center[1] + (self.size[1])),
                (self.center[0] - (self.size[0]), self.center[1] - (self.size[1])),
            ]
        )

    def build_point_tree(self, points):
        for index, p in enumerate(points):
            p_rect = (p[0], p[1], p[0], p[1])
            self.insert(p, p_rect, index)

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

    def insert(self, item, rect, index):
        rect = normalize_rect(rect)

        if len(self.children) == 0:
            node = QuadNode(item, rect, index)
            if item not in [node.item for node in self.nodes]:
                self.nodes.append(node)

            if len(self.nodes) > self.MAX and self.depth < self.MAX_DEPTH:
                self.split()
                return node
        else:
            return self.insert_into_children(item, rect, index)

    def insert_into_children(self, item, rect, index):
        # if rect spans center then insert here
        # NOTE: probably do not need this since rect[0] = rect[2] and rect[1] = rect[3] when we work with points only
        # so these conditions will never be true
        if (rect[0] <= self.center[0] and rect[2] > self.center[0]) and (
            rect[1] <= self.center[1] and rect[3] > self.center[1]
        ):
            node = QuadNode(item, rect, index)
            self.nodes.append(node)
            return node
        else:
            return_nodes = []
            # try to insert into children
            if rect[0] <= self.center[0]:
                if rect[1] <= self.center[1]:
                    # return self.children[0].insert(item, rect, index)
                    self.children[0].insert(item, rect, index)
                    # new_nodes = self.children[0].insert(item, rect, index)
                    # return_nodes.extend(new_nodes)
                if rect[3] >= self.center[1]:
                    # return self.children[1].insert(item, rect, index)
                    self.children[1].insert(item, rect, index)
                    # new_nodes = self.children[1].insert(item, rect, index)
                    # return_nodes.extend(new_nodes)
            if rect[2] >= self.center[0]:
                if rect[1] <= self.center[1]:
                    # return self.children[2].insert(item, rect, index)
                    self.children[2].insert(item, rect, index)
                    # new_nodes = self.children[2].insert(item, rect, index)
                    # return_nodes.extend(new_nodes)
                if rect[3] >= self.center[1]:
                    self.children[3].insert(item, rect, index)
            return return_nodes

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
            self.insert_into_children(node.item, node.rect, node.index)

    # def query_polygon(self, polygon, results=None):
    #     # intersect quad tree with a 2D polygon
    #     if results is None:
    #         results = set()

    #     # intersect the children with the polygon
    #     # TODO: here, we create None polygons... think about how to handle them
    #     if polygon is None:
    #         pass
    #     else:
    #         if len(self.children) > 0:

    #             # first slice vertically
    #             left_polygon, right_polygon = slice_in_two(polygon, self.center[0], 0)

    #             # then slice horizontally
    #             # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

    #             q1_polygon, q2_polygon = slice_in_two(left_polygon, self.center[1], 1)
    #             q3_polygon, q4_polygon = slice_in_two(right_polygon, self.center[1], 1)

    #             # now query these 4 polygons further down the quadtree
    #             self.children[0].query_polygon(q1_polygon, results)
    #             self.children[1].query_polygon(q2_polygon, results)
    #             self.children[2].query_polygon(q3_polygon, results)
    #             self.children[3].query_polygon(q4_polygon, results)

    #         for node in self.nodes:
    #             if node.is_contained_in(polygon):
    #                 results.add(node)

    #         return results

    def query_polygon(self, polygon, results=None):
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
            if polygon_points == self.quadrant_rectangle_points():
                for node in self.find_nodes_in():
                    results.add(node)
            else:
                if len(self.children) > 0:
                    # first slice vertically
                    left_polygon, right_polygon = slice_in_two(polygon, self.center[0], 0)

                    # then slice horizontally
                    # ie need to slice the left and right polygons each in two to have the 4 quadrant polygons

                    q1_polygon, q2_polygon = slice_in_two(left_polygon, self.center[1], 1)
                    q3_polygon, q4_polygon = slice_in_two(right_polygon, self.center[1], 1)

                    # now query these 4 polygons further down the quadtree
                    self.children[0].query_polygon(q1_polygon, results)
                    self.children[1].query_polygon(q2_polygon, results)
                    self.children[2].query_polygon(q3_polygon, results)
                    self.children[3].query_polygon(q4_polygon, results)

                for node in self.nodes:
                    if node.is_contained_in(polygon):
                        results.add(node)

            return results

    def find_nodes_in(self, results=None):
        # TODO: find the nodes that are in this subtree
        if results is None:
            results = set()
        if len(self.children) > 0:
            # there are children which we need to iterate through
            for child in self.children:
                child.find_nodes_in(results)
        for node in self.nodes:
            results.add(node)
        return results