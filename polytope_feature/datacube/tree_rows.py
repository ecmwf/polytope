"""One longitude leaf per latitude node for unions of non-orthogonal shapes (polygons, paths).

A polygon is sliced as a union of convex pieces (triangles), each into its own tree, and the trees are merged.  The
slicer used to leave the leaf (longitude) axis uncompressed for such unions so that merging de-duplicated points
shared by neighbouring pieces, at the cost of one tree node per point (~1.4 KB/point).  With :class:`RowMerger`
the leaf axis stays compressed: each piece gives one float64 leaf per latitude node, and merging concatenates the
leaves under the same latitude node into one sorted, de-duplicated array.

The merged leaf holds exactly the points, in the same (ascending) order, as the per-point leaves did.  Its
``_keep_value_order`` flag tells ``FDBDatacube.get``/``prepare`` to keep that order instead of reordering the
values by grid index, as they do for box leaves (on HEALPix nested grids the two orders differ), so results come
out in the order the per-point leaves gave.
"""

import numpy as np

from .tree_values import is_array


def _is_array_leaf(node, leaf_axis_name):
    return node.axis.name == leaf_axis_name and len(node.children) == 0 and is_array(node.values)


class RowMerger:
    """Merge per-piece slice trees, combining the leaves of each latitude node into one array leaf.

    Call :meth:`merge` for every piece's tree and :meth:`finalise` once at the end.  Leaf arrays are only
    concatenated in ``finalise``, so a row covered by many pieces is copied once.
    """

    def __init__(self, leaf_axis_name):
        self.leaf_axis_name = leaf_axis_name
        # id(leaf) -> (leaf, [values arrays to combine])
        self._pending = {}

    def merge(self, mine, other):
        mine.tags.update(other.tags)
        my_leaf = None
        for child in mine.children:
            if _is_array_leaf(child, self.leaf_axis_name):
                my_leaf = child
                break
        for other_child in list(other.children):
            if _is_array_leaf(other_child, self.leaf_axis_name):
                if my_leaf is None:
                    mine.add_child(other_child)
                    my_leaf = other_child
                    continue
                my_leaf.tags.update(other_child.tags)
                entry = self._pending.get(id(my_leaf))
                if entry is None:
                    entry = self._pending[id(my_leaf)] = (my_leaf, [my_leaf.values])
                entry[1].append(other_child.values)
                continue
            my_child = mine.find_child(other_child)
            if my_child is None:
                mine.add_child(other_child)
            else:
                self.merge(my_child, other_child)

    def finalise(self, tree):
        """Combine the pending leaves and give every leaf of ``tree`` sorted, unique values."""
        for leaf, arrays in self._pending.values():
            parent = leaf.parent
            parent.children.remove(leaf)
            leaf.values = np.sort(np.concatenate(arrays), kind="stable")
            parent.add_child(leaf)
        self._pending = {}
        stack = [tree]
        while stack:
            node = stack.pop()
            for child in list(node.children):
                if _is_array_leaf(child, self.leaf_axis_name):
                    child._keep_value_order = True
                    values = child.values
                    if len(values) > 1 and bool(np.any(values[1:] == values[:-1])):
                        # several pieces (or cyclic copies of one piece) gave the same point: keep it once
                        node.children.remove(child)
                        child.values = np.unique(values)
                        node.add_child(child)
                elif len(child.children) != 0:
                    stack.append(child)
        return tree
