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

# """
# # Pyqtree

# Pyqtree is a pure Python spatial index for GIS or rendering usage.
# It stores and quickly retrieves items from a 2x2 rectangular grid area,
# and grows in depth and detail as more items are added.
# The actual quad tree implementation is adapted from
# [Matt Rasmussen's compbio library](https://github.com/mdrasmus/compbio/blob/master/rasmus/quadtree.py)
# and extended for geospatial use.


# ## Platforms

# Python 2 and 3.


# ## Dependencies

# Pyqtree is written in pure Python and has no dependencies.


# ## Installing It

# Installing Pyqtree can be done by opening your terminal or commandline and typing:

#     pip install pyqtree

# Alternatively, you can simply download the "pyqtree.py" file and place
# it anywhere Python can import it, such as the Python site-packages folder.


# ## Example Usage

# Start your script by importing the quad tree.

#     from pyqtree import Index

# Setup the spatial index, giving it a bounding box area to keep track of.
# The bounding box being in a four-tuple: (xmin, ymin, xmax, ymax).

#     spindex = Index(bbox=(0, 0, 100, 100))

# Populate the index with items that you want to be retrieved at a later point,
# along with each item's geographic bbox.

#     # this example assumes you have a list of items with bbox attribute
#     for item in items:
#         spindex.insert(item, item.bbox)

# Then when you have a region of interest and you wish to retrieve items from that region,
# just use the index's intersect method. This quickly gives you a list of the stored items
# whose bboxes intersects your region of interests.

#     overlapbbox = (51, 51, 86, 86)
#     matches = spindex.intersect(overlapbbox)

# There are other things that can be done as well, but that's it for the main usage!


# ## More Information:

# - [Home Page](http://github.com/karimbahgat/Pyqtree)
# - [API Documentation](https://karimbahgat.github.io/Pyqtree/)


# ## License:

# This code is free to share, use, reuse, and modify according to the MIT license, see LICENSE.txt.


# ## Credits:

# - Karim Bahgat
# - Joschua Gandert

# """


# def _normalize_rect(rect):
#     if len(rect) == 2:
#         x1, y1 = rect
#         x2, y2 = rect
#     else:
#         x1, y1, x2, y2 = rect
#     if x1 > x2:
#         x1, x2 = x2, x1
#     if y1 > y2:
#         y1, y2 = y2, y1
#     return (x1, y1, x2, y2)


# def _loopallchildren(parent):
#     for child in parent.children:
#         if child.children:
#             for subchild in _loopallchildren(child):
#                 yield subchild
#         yield child


# class _QuadNode(object):
#     def __init__(self, item, rect):
#         self.item = item
#         self.rect = rect

#     def __eq__(self, other):
#         return self.item == other.item and self.rect == other.rect

#     def __hash__(self):
#         return hash(self.item)


# class _QuadTree(object):
#     """
#     Internal backend version of the index.
#     The index being used behind the scenes. Has all the same methods as the user
#     index, but requires more technical arguments when initiating it than the
#     user-friendly version.
#     """

#     def __init__(self, x=0, y=0, width=360, height=180, max_items=4, max_depth=10, _depth=0):
#         self.nodes = []
#         self.children = []
#         self.center = (x, y)
#         self.width, self.height = width, height
#         self.max_items = max_items
#         self.max_depth = max_depth
#         self._depth = _depth

#     def build_point_tree(self, points):
#         for p in points:
#             p_rect = (p[0], p[1], p[0], p[1])
#             self._insert(p, p_rect)

#     def pprint(self):
#         if self._depth == 0:
#             print("\n")
#         if len(self.children) == 0:
#             for n in self.nodes:
#                 print("\t" * (self._depth + 1) + "\u21b3" + str(n.rect[0]) + " , " + str(n.rect[1]))
#         for child in self.children:
#             print("\t" * (self._depth + 1) + "\u21b3" + "None")
#             child.pprint()

#     def _insert(self, item, bbox):
#         rect = _normalize_rect(bbox)
#         if len(self.children) == 0:
#             node = _QuadNode(item, rect)
#             self.nodes.append(node)

#             if len(self.nodes) > self.max_items and self._depth < self.max_depth:
#                 print(item)
#                 print(len(self.nodes))
#                 self._split()
#         else:
#             self._insert_into_children(item, rect)

#     def _remove(self, item, bbox):
#         rect = _normalize_rect(bbox)
#         if len(self.children) == 0:
#             node = _QuadNode(item, rect)
#             self.nodes.remove(node)
#         else:
#             self._remove_from_children(item, rect)

#     def _intersect(self, rect, results=None, uniq=None):
#         if results is None:
#             rect = _normalize_rect(rect)
#             results = []
#             uniq = set()
#         # search children
#         if self.children:
#             if rect[0] <= self.center[0]:
#                 if rect[1] <= self.center[1]:
#                     self.children[0]._intersect(rect, results, uniq)
#                 if rect[3] >= self.center[1]:
#                     self.children[1]._intersect(rect, results, uniq)
#             if rect[2] >= self.center[0]:
#                 if rect[1] <= self.center[1]:
#                     self.children[2]._intersect(rect, results, uniq)
#                 if rect[3] >= self.center[1]:
#                     self.children[3]._intersect(rect, results, uniq)
#         # search node at this level
#         for node in self.nodes:
#             _id = id(node.item)
#             if (_id not in uniq and
#                 node.rect[2] >= rect[0] and node.rect[0] <= rect[2] and
#                 node.rect[3] >= rect[1] and node.rect[1] <= rect[3]):
#                 results.append(node.item)
#                 uniq.add(_id)
#         return results

#     def _insert_into_children(self, item, rect):
#         # if rect spans center then insert here
#         if (rect[0] <= self.center[0] and rect[2] >= self.center[0] and
#             rect[1] <= self.center[1] and rect[3] >= self.center[1]):
#             node = _QuadNode(item, rect)
#             self.nodes.append(node)
#         else:
#             print("not here")
#             # try to insert into children
#             if rect[0] <= self.center[0]:
#                 if rect[1] <= self.center[1]:
#                     self.children[0]._insert(item, rect)
#                 if rect[3] >= self.center[1]:
#                     self.children[1]._insert(item, rect)
#             if rect[2] > self.center[0]:
#                 if rect[1] <= self.center[1]:
#                     self.children[2]._insert(item, rect)
#                 if rect[3] >= self.center[1]:
#                     self.children[3]._insert(item, rect)

#     def _remove_from_children(self, item, rect):
#         # if rect spans center then insert here
#         if (rect[0] <= self.center[0] and rect[2] >= self.center[0] and
#             rect[1] <= self.center[1] and rect[3] >= self.center[1]):
#             node = _QuadNode(item, rect)
#             self.nodes.remove(node)
#         else:
#             # try to remove from children
#             if rect[0] <= self.center[0]:
#                 if rect[1] <= self.center[1]:
#                     self.children[0]._remove(item, rect)
#                 if rect[3] >= self.center[1]:
#                     self.children[1]._remove(item, rect)
#             if rect[2] > self.center[0]:
#                 if rect[1] <= self.center[1]:
#                     self.children[2]._remove(item, rect)
#                 if rect[3] >= self.center[1]:
#                     self.children[3]._remove(item, rect)

#     def _split(self):
#         print("inside split")
#         quartwidth = self.width / 4.0
#         quartheight = self.height / 4.0
#         halfwidth = self.width / 2.0
#         halfheight = self.height / 2.0
#         x1 = self.center[0] - quartwidth
#         x2 = self.center[0] + quartwidth
#         y1 = self.center[1] - quartheight
#         y2 = self.center[1] + quartheight
#         print(x1,y1,x2,y2)
#         new_depth = self._depth + 1
#         self.children = [_QuadTree(x1, y1, halfwidth, halfheight,
#                                    self.max_items, self.max_depth, new_depth),
#                          _QuadTree(x1, y2, halfwidth, halfheight,
#                                    self.max_items, self.max_depth, new_depth),
#                          _QuadTree(x2, y1, halfwidth, halfheight,
#                                    self.max_items, self.max_depth, new_depth),
#                          _QuadTree(x2, y2, halfwidth, halfheight,
#                                    self.max_items, self.max_depth, new_depth)]
#         nodes = self.nodes
#         self.nodes = []
#         for node in nodes:
#             self._insert_into_children(node.item, node.rect)

#     def __len__(self):
#         """
#         Returns:

#         - A count of the total number of members/items/nodes inserted
#         into this quadtree and all of its child trees.
#         """
#         size = 0
#         for child in self.children:
#             size += len(child)
#         size += len(self.nodes)
#         return size


class QuadTreeSlicer(Engine):
    def __init__(self, points):
        # TODO: here need to construct quadtree, which is specific to datacube
        quad_tree = QuadTree()
        quad_tree.build_point_tree(points)
        self.quad_tree = quad_tree

    # TODO: method to slice polygon against quadtree
