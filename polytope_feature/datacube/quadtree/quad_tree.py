import heapq

from ...engine.slicing_tools import slice, slice_in_two

"""

    QuadTree data structure

    comes from: https://github.com/mdrasmus/compbio/blob/master/rasmus/quadtree.py

    is specific to 2D

"""


class QuadNode:
    def __init__(self, item, index):
        self.item = item
        self.index = index

    def is_contained_in(self, polygon):
        # implement method to check if the node point is inside the polygon
        # TODO: could consider doing this through a point in polygon check?
        node_x, node_y = self.item

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
        self.center = (x, y)
        self.size = tuple(size)
        self.depth = depth
        self.node_items = set()

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
        # TODO: SLOW, scales linearly with number of points
        for index, p in enumerate(points):
            self.insert(tuple(p), index)

    def pprint(self):
        if self.depth == 0:
            print("\n")
        if len(self.children) == 0:
            for n in self.nodes:
                print("\t" * (self.depth + 1) + "\u21b3" + str(n.item[0]) + " , " + str(n.item[1]))
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

    def insert(self, item, index):
        if not self.children:
            node = QuadNode(item, index)
            if item not in self.node_items:
                self.nodes.append(node)
                self.node_items.add(node.item)

            if len(self.nodes) > self.MAX and self.depth < self.MAX_DEPTH:
                self.split()
                return node
        else:
            return self.insert_into_children(item, index)

    def insert_into_children(self, item, index):
        x, y = item
        cx, cy = self.center
        # try to insert into children
        if x <= cx:
            if y <= cy:
                self.children[0].insert(item, index)
            if y >= cy:
                self.children[1].insert(item, index)
        if x >= cx:
            if y <= cy:
                self.children[2].insert(item, index)
            if y >= cy:
                self.children[3].insert(item, index)

    def split(self):
        half_size = [s / 2 for s in self.size]
        x_center, y_center = self.center[0], self.center[1]
        hx, hy = half_size

        new_centers = [
            (x_center - hx, y_center - hy),
            (x_center - hx, y_center + hy),
            (x_center + hx, y_center - hy),
            (x_center + hx, y_center + hy),
        ]

        self.children = [
            QuadTree(new_center[0], new_center[1], half_size, self.depth + 1) for new_center in new_centers
        ]

        nodes = self.nodes
        self.nodes = []
        for node in nodes:
            self.insert_into_children(node.item, node.index)

    def query_polygon(self, polygon, results=None):
        # TODO: would be like uniform rust + python API with
        # intersect quad tree with a 2D polygon
        if results is None:
            results = set()

        # intersect the children with the polygon
        if polygon is None:
            pass
        else:
            polygon_points = set([tuple(point) for point in polygon.points])
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

                results.update(node for node in self.nodes if node.is_contained_in(polygon))

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

    def _box_dist2(self, query):
        """Squared distance from query point to the nearest point inside this node's bounding box.
        Returns 0 if the query point is inside the box.
        `self.size` stores half-extents on each axis."""
        qx, qy = query
        cx, cy = self.center
        sx, sy = self.size
        dx = max(0.0, abs(qx - cx) - sx)
        dy = max(0.0, abs(qy - cy) - sy)
        return dx * dx + dy * dy

    def _knn_search(self, query, k, heap, seen, counter):
        """Branch-and-bound kNN traversal.
        heap: max-heap (via negation) of (-dist2, counter, QuadNode) for current k-best.
        seen: set of node indices already in the heap (avoids duplicates from shared-boundary insertions).
        counter: single-element list used as a monotone tie-breaker."""
        # Prune: if the closest possible point in this box is farther than
        # the k-th best distance found so far, skip the entire subtree.
        prune_dist2 = -heap[0][0] if len(heap) >= k else float("inf")
        if self._box_dist2(query) > prune_dist2:
            return

        if not self.children:
            # Leaf node: evaluate every stored point.
            for node in self.nodes:
                if node.index in seen:
                    continue
                d2 = (node.item[0] - query[0]) ** 2 + (node.item[1] - query[1]) ** 2
                if len(heap) < k:
                    heapq.heappush(heap, (-d2, counter[0], node))
                    seen.add(node.index)
                    counter[0] += 1
                elif d2 < -heap[0][0]:
                    _, _, evicted = heapq.heapreplace(heap, (-d2, counter[0], node))
                    seen.discard(evicted.index)
                    seen.add(node.index)
                    counter[0] += 1
        else:
            for child in self.children:
                child._knn_search(query, k, heap, seen, counter)

    def k_nearest_neighbor(self, query, k, points=None):
        """Return list of up to k nearest QuadNode objects to query, sorted nearest-first.

        Args:
            query:  (x, y) query coordinates.
            k:      number of nearest neighbours to return.
            points: ignored; accepted for API compatibility with the Rust version.

        Returns:
            List of QuadNode objects ordered from nearest to farthest.
        """
        heap = []  # max-heap via negation: (-dist2, counter, QuadNode)
        seen = set()
        counter = [0]
        self._knn_search(query, k, heap, seen, counter)
        # Sort nearest-first: ascending dist2 == descending (-dist2)
        heap.sort(reverse=True)
        return [node for _neg_d2, _c, node in heap]
