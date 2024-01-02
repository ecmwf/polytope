from .engine import Engine

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
            print("\t" * (self.depth + 1) + "\u21b3" + str(child.center[0]-child.size[0]) + " , " + str(child.center[1] - child.size[1]) + " , " + str(child.center[0]+child.size[0]) + " , " + str(child.center[1] + child.size[1]))
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
        if ((rect[0] <= self.center[0] and rect[2] > self.center[0]) and
                (rect[1] <= self.center[1] and rect[3] > self.center[1])):
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
        self.children = [QuadTree(self.center[0] - self.size[0]/2,
                                  self.center[1] - self.size[1]/2,
                                  [s/2 for s in self.size], self.depth + 1),
                         QuadTree(self.center[0] - self.size[0]/2,
                                  self.center[1] + self.size[1]/2,
                                  [s/2 for s in self.size], self.depth + 1),
                         QuadTree(self.center[0] + self.size[0]/2,
                                  self.center[1] - self.size[1]/2,
                                  [s/2 for s in self.size], self.depth + 1),
                         QuadTree(self.center[0] + self.size[0]/2,
                                  self.center[1] + self.size[1]/2,
                                  [s/2 for s in self.size], self.depth + 1)]

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

    def query_polygon(self, polygon):
        # TODO: intersect quad tree with a 2D polygon
        pass


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
