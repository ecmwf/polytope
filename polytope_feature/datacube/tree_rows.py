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

Each piece's leaf carries that piece's tag, so a union of differently tagged shapes (several polygons, several
tagged Points on a structured grid) would lose information if the merged leaf carried one set of tags for all of
its points.  The merged leaf therefore gets per-point tags (``set_point_tags``) whenever its pieces disagree, and
a point selected by several pieces carries the union of their tags; this is what lets such unions stay compressed
instead of falling back to one node per point.
"""

import numpy as np

from .tree_values import is_array

__all__ = ["RowMerger"]


def _is_array_leaf(node, leaf_axis_name):
    return node.axis.name == leaf_axis_name and len(node.children) == 0 and is_array(node.values)


def _piece_tag_ids(pieces):
    """``(tag_sets, ids)`` of the pieces of one row, or None when every piece carries the same tags."""
    tag_sets = []
    ids_of = {}
    ids = []
    for _, tags in pieces:
        key = frozenset(tags)
        tag_id = ids_of.get(key)
        if tag_id is None:
            tag_id = ids_of[key] = len(tag_sets)
            tag_sets.append(key)
        ids.append(tag_id)
    if len(tag_sets) < 2:
        return None, None
    return tag_sets, np.asarray(ids, dtype=np.int32)


def _union_duplicate_tags(values, tag_sets, tag_ids):
    """Tag ids of the unique ``values``, unioning the tags of every repeat of a value."""
    unique, start, counts = np.unique(values, return_index=True, return_counts=True)
    ids = tag_ids[start]
    tag_sets = list(tag_sets)
    ids_of = {tags: i for i, tags in enumerate(tag_sets)}
    for group in np.flatnonzero(counts > 1):
        at = start[group]
        group_ids = tag_ids[at : at + counts[group]]  # noqa: E203
        if np.all(group_ids == group_ids[0]):
            continue
        key = frozenset().union(*(tag_sets[i] for i in group_ids.tolist()))
        tag_id = ids_of.get(key)
        if tag_id is None:
            tag_id = ids_of[key] = len(tag_sets)
            tag_sets.append(key)
        ids[group] = tag_id
    return unique, tag_sets, ids


class RowMerger:
    """Merge per-piece slice trees, combining the leaves of each latitude node into one array leaf.

    Call :meth:`merge` for every piece's tree and :meth:`finalise` once at the end.  Leaf arrays are only
    concatenated in ``finalise``, so a row covered by many pieces is copied once.
    """

    def __init__(self, leaf_axis_name):
        self.leaf_axis_name = leaf_axis_name
        # id(leaf) -> (leaf, [(values array, tags) to combine])
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
                entry = self._pending.get(id(my_leaf))
                if entry is None:
                    entry = self._pending[id(my_leaf)] = (my_leaf, [(my_leaf.values, set(my_leaf.tags))])
                entry[1].append((other_child.values, other_child.tags))
                my_leaf.tags.update(other_child.tags)
                continue
            my_child = mine.find_child(other_child)
            if my_child is None:
                mine.add_child(other_child)
            else:
                self.merge(my_child, other_child)

    def finalise(self, tree):
        """Combine the pending leaves and give every leaf of ``tree`` sorted, unique values."""
        for leaf, pieces in self._pending.values():
            parent = leaf.parent
            parent.children.remove(leaf)
            tag_sets, piece_ids = _piece_tag_ids(pieces)
            values = np.concatenate([piece[0] for piece in pieces])
            order = np.argsort(values, kind="stable")
            leaf.values = values[order]
            if piece_ids is not None:
                lengths = np.asarray([len(piece[0]) for piece in pieces], dtype=np.int64)
                leaf.set_point_tags(tag_sets, np.repeat(piece_ids, lengths)[order])
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
                        if child.tag_ids is None:
                            child.values = np.unique(values)
                        else:
                            unique, tag_sets, tag_ids = _union_duplicate_tags(values, child.tag_sets, child.tag_ids)
                            child.values = unique
                            child.set_point_tags(tag_sets, tag_ids)
                        node.add_child(child)
                elif len(child.children) != 0:
                    stack.append(child)
        return tree
