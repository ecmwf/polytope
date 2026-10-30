import logging
from copy import copy
from typing import Optional, OrderedDict

import numpy as np
from sortedcontainers import SortedList

from .datacube_axis import IntDatacubeAxis, UnsliceableDatacubeAxis

# ---------------------------------------------------------------------------
# Value helpers: a node's ``values`` is either a tuple (the common case) or a 1-D ``np.ndarray``.
#
# Non-leaf nodes keep their values as small hashable tuples.  Leaf nodes on the last (longitude)
# axis built by the hull slicer store their values as a float64 array instead (~8 B/point instead
# of ~32 B/point for a tuple of Python floats).  These helpers give both representations the same
# ordering, equality and hashing semantics that the tuple representation always had.
# ---------------------------------------------------------------------------


def is_array(values):
    return isinstance(values, np.ndarray)


def values_identical(a, b):
    """Exact element-wise equality, equivalent to ``a == b`` for two tuples."""
    if not is_array(a) and not is_array(b):
        return a == b
    if len(a) != len(b):
        return False
    return bool(np.array_equal(np.asarray(a), np.asarray(b)))


def values_within_tol(a, b, tol):
    """True unless some pair of elements differs by more than ``tol`` (NaN never counts as a difference)."""
    diff = np.abs(np.asarray(a, dtype=np.float64) - np.asarray(b, dtype=np.float64))
    return not bool(np.any(diff > tol))


def values_lt(a, b):
    """Lexicographic ``a < b``, equivalent to tuple comparison."""
    if not is_array(a) and not is_array(b):
        return a < b
    a = np.asarray(a)
    b = np.asarray(b)
    n = min(len(a), len(b))
    differing = np.flatnonzero(a[:n] != b[:n])
    if differing.size:
        i = differing[0]
        return bool(a[i] < b[i])
    return len(a) < len(b)


def values_hash_key(values):
    """A hashable key equal to the tuple of the same values (so tuple and array nodes hash alike)."""
    if is_array(values):
        return tuple(values.tolist())
    return values


def remove_value(values, value):
    """Drop every element equal to ``value``, preserving the container type."""
    if is_array(values):
        return values[values != value]
    return tuple(val for val in values if val != value)


def merge_sorted(values, new_values):
    """Return ``values`` extended with ``new_values`` and sorted, as a float64 array."""
    combined = np.concatenate([np.asarray(values, dtype=np.float64), np.asarray(new_values, dtype=np.float64)])
    return np.sort(combined, kind="stable")


def result_as_array(result):
    """Return a leaf ``result`` as a float64 array, with missing (``None``) values as NaN."""
    if is_array(result) and result.dtype != object:
        return result.astype(np.float64, copy=False)
    return np.array([np.nan if v is None else v for v in result], dtype=np.float64)


class DatacubePath(OrderedDict):
    def values(self):
        return tuple(super().values())

    def keys(self):
        return tuple(super().keys())

    def pprint(self):
        result = ""
        for k, v in self.items():
            result += f"{k}={v},"
        print(result[:-1])


class MergedTensorIndexNode(object):
    def __init__(self, axes=None, values=tuple()):
        # TODO
        self.axes = axes
        self.values = values
        self.children = SortedList()
        self._parent = None
        self.indexes = []
        self.result = []
        self.hidden = False
        self.ancestors = []
        self.axis = axes[0] if axes is not None else None
        self.tags = set()

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __delitem__(self, key):
        return delattr(self, key)

    def __lt__(self, other):
        return ((self.axes[0].name, self.axes[1].name), self.values) < (
            (other.axes[0].name, other.axes[1].name),
            other.values,
        )

    def __eq__(self, other):
        if not isinstance(other, MergedTensorIndexNode):
            return False
        if self.axes[0].name == other.axes[0].name and self.axes[1].name == other.axes[1].name:
            if other.values == self.values:
                return True
        return False

    # def __hash__(self):
    #     return hash((self.axes[0].name, self.axes[1].name, self.values))

    def _collect_leaf_nodes(self, leaves):
        if len(self.children) == 0:
            leaves.append(self)

    def flatten(self):
        path = DatacubePath()
        ancestors = self.get_ancestors()
        for ancestor in ancestors:
            if isinstance(ancestor, TensorIndexTree):
                path[ancestor.axis.name] = ancestor.values
            else:
                path[ancestor.axes[0].name] = [ancestor.values[0]]
                path[ancestor.axes[1].name] = [ancestor.values[1]]
        return path

    @property
    def parent(self):
        return self._parent

    def get_ancestors(self):
        ancestors = []
        current_node = self
        while current_node.axis.name != "root":
            ancestors.append(current_node)
            current_node = current_node.parent
        return ancestors[::-1]

    def pprint(self, level=0):
        if self.axis.name == "root":
            logging.debug("\n")
        logging.debug("\t" * level + "\u21b3" + str(self))
        for child in self.children:
            if not child.hidden:
                child.pprint(level + 1)
        if len(self.children) == 0:
            logging.debug("\t" * (level + 1) + "\u21b3" + str(self.result))

    def __repr__(self):
        if self.axis != "root":
            # return f"{self.axes[0].name}={self.values[0]}, {self.axes[1].name}={self.values[1]}"
            return f"{(self.axes[0].name, self.axes[1].name)}={self.values}"
        else:
            return f"{self.axis}"

    def remove_branch(self):
        if not self.is_root():
            old_parent = self._parent
            # print("WHAT WHEN WE REMOVE BRANCHES??")
            # print([c for c in self._parent.children])
            # print(self)
            self._parent.children.remove(self)
            self._parent = None
            if len(old_parent.children) == 0:
                old_parent.remove_branch()

    def result_array(self):
        """This node's ``result`` as a float64 array, with missing values (``None``) as NaN."""
        return result_as_array(self.result)

    def is_root(self):
        return self.parent is None

    def merge(self, other):
        self.tags.update(other.tags)
        for other_child in other.children:
            my_child = self.find_child(other_child)
            if not my_child:
                self.add_child(other_child)
            else:
                my_child.merge(other_child)

    def add_child(self, node):
        self.children.add(node)
        node._parent = self

    def find_child(self, node):
        index = self.children.bisect_left(node)
        if index < len(self.children) and self.children[index] == node:
            return self.children[index]
        return None


def _tag_table(point_tags, n_points):
    """``(tag_sets, tag_ids)`` of a sequence of per-point tag sets.

    ``tag_ids`` is None when every point carries the same tags (the usual case), which keeps a fold of
    one shape from paying 4 bytes a point for a constant.
    """
    if point_tags is None:
        return [frozenset()], None
    tag_sets = []
    ids_of = {}
    tag_ids = np.empty(len(point_tags), dtype=np.int32)
    for i, tags in enumerate(point_tags):
        key = frozenset(tags)
        tag_id = ids_of.get(key)
        if tag_id is None:
            tag_id = ids_of[key] = len(tag_sets)
            tag_sets.append(key)
        tag_ids[i] = tag_id
    if len(tag_sets) < 2:
        return tag_sets or [frozenset()], None
    return tag_sets, tag_ids


def _merge_tag_tables(first, second, indexes):
    """The tag table of two concatenated bulk nodes, unioning the tags of points sharing an index."""
    tag_sets = list(first.tag_sets)
    ids_of = {tags: i for i, tags in enumerate(tag_sets)}
    offsets = np.empty(len(second.tag_sets), dtype=np.int32)
    for i, tags in enumerate(second.tag_sets):
        tag_id = ids_of.get(tags)
        if tag_id is None:
            tag_id = ids_of[tags] = len(tag_sets)
            tag_sets.append(tags)
        offsets[i] = tag_id
    tag_ids = np.concatenate([first.expanded_tag_ids(), offsets[second.expanded_tag_ids()]])
    # the tags of every occurrence of a repeated index are unioned onto its first occurrence
    order = np.argsort(indexes, kind="stable")
    sorted_indexes = indexes[order]
    _, start, counts = np.unique(sorted_indexes, return_index=True, return_counts=True)
    for group in np.flatnonzero(counts > 1):
        positions = order[start[group] : start[group] + counts[group]]  # noqa: E203
        group_ids = tag_ids[positions]
        if np.all(group_ids == group_ids[0]):
            continue
        key = frozenset().union(*(tag_sets[i] for i in group_ids.tolist()))
        tag_id = ids_of.get(key)
        if tag_id is None:
            tag_id = ids_of[key] = len(tag_sets)
            tag_sets.append(key)
        tag_ids[positions] = tag_id
    return tag_sets, tag_ids


class BulkMergedTensorIndexNode(MergedTensorIndexNode):
    """Array-backed coupled-axis leaf.

    This is the bulk equivalent of many ``MergedTensorIndexNode`` objects. It
    keeps explicit coordinates and canonical backend indexes without expanding
    every selected point into a Python tree node.

    ``coordinates`` is an (N, 2) array of (first axis, second axis) values, ie
    (lat, lon), and ``indexes`` the N canonical backend indexes of those points.
    After retrieval, ``result`` holds one array of N values per uncompressed
    request combination of the compressed axes above this node, in the same
    order as the legacy leaves' flat ``result`` blocks.

    Tags are stored per point without a Python object per point: ``tag_sets`` is
    the list of distinct tag sets of the selection and ``tag_ids`` an int32 array
    naming one of them per point. ``tags`` (inherited) holds their union.

    At most one bulk node exists per parent: bulk nodes on the same axes compare
    equal, so merging trees (eg. for unions) unions their points instead of
    adding siblings.
    """

    def __init__(self, axes, coordinates, indexes, point_tags=None, tag_ids=None, tag_sets=None):
        super().__init__(axes, ())
        self.coordinates = np.asarray(coordinates, dtype=np.float64).reshape(-1, 2)
        self.indexes = None if indexes is None else np.asarray(indexes, dtype=np.int64)
        if tag_sets is not None:
            self.tag_sets = [frozenset(t) for t in tag_sets] or [frozenset()]
            self.tag_ids = None if tag_ids is None else np.asarray(tag_ids, dtype=np.int32)
        else:
            self.tag_sets, self.tag_ids = _tag_table(point_tags, len(self.coordinates))
            if point_tags is not None:
                assert len(point_tags) == len(self.coordinates)
        assert self.tag_ids is None or len(self.tag_ids) == len(self.coordinates)
        for t in self.tag_sets:
            self.tags.update(t)

    def tags_of_point(self, i):
        """The tags of point ``i`` of this node (a frozenset; empty when the point carries none)."""
        if self.tag_ids is None:
            return self.tag_sets[0]
        return self.tag_sets[self.tag_ids[i]]

    def expanded_tag_ids(self):
        """``tag_ids`` as an array, materialised when every point of the node shares one tag set."""
        if self.tag_ids is not None:
            return self.tag_ids
        return np.zeros(self.point_count, dtype=np.int32)

    def copy_shared(self):
        """An unattached copy of this node holding no result and sharing all of its arrays.

        Used by ``TensorIndexTree.prune`` to put the same points into another tree without copying
        anything per point.
        """
        new = copy(self)
        new.result = []
        new._parent = None
        new.children = SortedList()
        new.ancestors = []
        new.tags = set(self.tags)
        return new

    @property
    def point_count(self):
        return len(self.coordinates)

    @property
    def axis_names(self):
        return tuple(axis.name for axis in self.axes)

    def __lt__(self, other):
        # Bulk nodes on the same axes are interchangeable in sort order; they sort after any other node.
        if isinstance(other, BulkMergedTensorIndexNode):
            return self.axis_names < other.axis_names
        return False

    def __eq__(self, other):
        return isinstance(other, BulkMergedTensorIndexNode) and self.axis_names == other.axis_names

    def __repr__(self):
        return f"{self.axis_names}=<bulk {self.point_count} points>"

    def flatten(self):
        path = self.parent.flatten() if self.parent is not None else DatacubePath()
        path[self.axes[0].name] = tuple(self.coordinates[:, 0].tolist())
        path[self.axes[1].name] = tuple(self.coordinates[:, 1].tolist())
        return path

    def get_ancestors(self):
        ancestors = self.parent.get_ancestors() if self.parent is not None else []
        return ancestors + [self]

    def merge(self, other):
        self.tags.update(other.tags)
        if other is self or other.point_count == 0:
            return
        if len(self.result) != 0 or len(other.result) != 0:
            raise ValueError("Cannot merge bulk nodes which already hold retrieved results")
        coordinates = np.concatenate([self.coordinates, other.coordinates])
        indexes = np.concatenate([self.indexes, other.indexes])
        tag_sets, tag_ids = _merge_tag_tables(self, other, indexes)
        # Points selected by both nodes keep the union of their tags
        _, first = np.unique(indexes, return_index=True)
        coordinates = coordinates[first]
        order = np.lexsort((coordinates[:, 1], coordinates[:, 0]))
        keep = first[order]
        self.coordinates = coordinates[order]
        self.indexes = indexes[keep]
        self.tag_sets = tag_sets
        self.tag_ids = tag_ids[keep]


class BulkGridTensorIndexNode(BulkMergedTensorIndexNode):
    """Array-backed leaf for a structured (hullslicer) lat/lon selection.

    Replaces the ``latitude -> longitude`` layers under one path: ``lat_values``
    holds the selected latitudes and ``lon_values[i]`` the (compressed)
    longitudes selected on latitude ``i``. The points, and so ``coordinates``,
    ``indexes`` and each ``result`` array, are ordered latitude-major, with the
    points of row ``i`` at ``row_slice(i)``; ``lon_values[i]`` is a view on
    ``coordinates``, not a second copy of the longitudes.

    Pass ``row_lengths`` together with flat ``coordinates`` to build the node from
    arrays that are already concatenated (what folding a prepared tree gives);
    otherwise ``lon_values`` is the list of per-row longitude arrays.
    """

    #: Set on a node built by the batched nearest-point search (:mod:`polytope_feature.engine.nearest_grid`):
    #: for every query point of the request, in request order, the index of the point of this node it
    #: resolved to.  Several queries share a point when they are nearest to the same grid point, so this is
    #: what a caller needs to report one result per *requested* point.  None on any other node.
    point_of_query: Optional[np.ndarray] = None

    def __init__(
        self,
        axes,
        lat_values,
        lon_values,
        indexes=None,
        point_tags=None,
        tag_ids=None,
        tag_sets=None,
        row_lengths=None,
        coordinates=None,
    ):
        self.lat_values = np.asarray(lat_values, dtype=np.float64)
        if row_lengths is None:
            lon_values = [np.asarray(lons, dtype=np.float64) for lons in lon_values]
            row_lengths = np.array([len(lons) for lons in lon_values], dtype=np.int64)
            if len(lon_values) == 0:
                coordinates = np.empty((0, 2))
            else:
                coordinates = np.column_stack((np.repeat(self.lat_values, row_lengths), np.concatenate(lon_values)))
        else:
            row_lengths = np.asarray(row_lengths, dtype=np.int64)
        self.row_offsets = np.concatenate([[0], np.cumsum(row_lengths)])
        super().__init__(axes, coordinates, indexes, point_tags, tag_ids, tag_sets)
        # the longitudes of a row are a view on the node's coordinates
        self.lon_values = [self.coordinates[self.row_slice(i), 1] for i in range(len(self.lat_values))]

    def row_slice(self, i):
        return slice(int(self.row_offsets[i]), int(self.row_offsets[i + 1]))

    def __repr__(self):
        return f"{self.axis_names}=<grid {len(self.lat_values)} rows, {self.point_count} points>"

    def merge(self, other):
        if other is self:
            return
        raise NotImplementedError("Bulk grid nodes are built after slicing and cannot be merged")


class TensorIndexTree(object):
    root = IntDatacubeAxis()
    root.name = "root"
    # Set on the merged longitude leaves of polygons/paths (see RowMerger below): FDBDatacube.get keeps their
    # values in ascending order instead of reordering them by grid index.
    _keep_value_order = False
    # Per-point tags of an array leaf whose points do not all carry the same tags (the merged rows of a union of
    # differently tagged shapes): an int32 id per value into ``tag_sets``.  ``tags`` holds their union, as for any
    # other node.  Both are None on a node whose points share ``tags``.
    tag_ids = None
    tag_sets = None

    def tags_of_point(self, i):
        """The tags of value ``i`` of this node: its own when they differ per point, else the node's."""
        if self.tag_ids is None:
            return self.tags
        return self.tag_sets[self.tag_ids[i]]

    def set_point_tags(self, tag_sets, tag_ids):
        """Give this node per-point tags; ``tags`` becomes their union."""
        self.tag_sets = [frozenset(t) for t in tag_sets]
        self.tag_ids = np.asarray(tag_ids, dtype=np.int32)
        self.tags = set()
        for t in self.tag_sets:
            self.tags.update(t)

    def __init__(self, axis=root, values=tuple()):
        # NOTE: the values here is a tuple so we can hash it. Leaves on the last (longitude) axis built by the hull
        # slicer hold a float64 np.ndarray instead; see tensor_index_tree.py for the shared comparison semantics.
        self.values = values
        self.children = SortedList()
        self._parent = None
        self.result = []
        self.axis = axis
        self.ancestors = []
        self.indexes = []
        self.hidden = False
        self.tags = set()

    @property
    def leaves(self):
        leaves = []
        self._collect_leaf_nodes(leaves)
        return leaves

    def _collect_leaf_nodes(self, leaves):
        if len(self.children) == 0:
            leaves.append(self)
            self.ancestors.append(self)
        for n in self.children:
            for ancestor in self.ancestors:
                n.ancestors.append(ancestor)
            if self.axis != TensorIndexTree.root:
                n.ancestors.append(self)
            n._collect_leaf_nodes(leaves)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __delitem__(self, key):
        return delattr(self, key)

    def __hash__(self):
        return hash((self.axis.name, values_hash_key(self.values)))

    def __eq__(self, other):
        if not isinstance(other, TensorIndexTree):
            return False
        if self.axis.name != other.axis.name:
            return False
        else:
            if values_identical(other.values, self.values):
                return True
            else:
                if isinstance(self.axis, UnsliceableDatacubeAxis):
                    return False
                else:
                    if len(other.values) != len(self.values):
                        return False
                    if self.axis.can_round and (is_array(self.values) or is_array(other.values)):
                        return values_within_tol(other.values, self.values, 2 * max(other.axis.tol, self.axis.tol))
                    for i in range(len(other.values)):
                        other_val = other.values[i]
                        self_val = self.values[i]
                        if self.axis.can_round:
                            if abs(other_val - self_val) > 2 * max(other.axis.tol, self.axis.tol):
                                return False
                        else:
                            if other_val != self_val:
                                return False
                    return True

    def __lt__(self, other):
        if self.axis.name != other.axis.name:
            return self.axis.name < other.axis.name
        return values_lt(self.values, other.values)

    def __repr__(self):
        if self.axis != "root":
            return f"{self.axis.name}={self.values}"
        else:
            return f"{self.axis}"

    def add_child(self, node):
        self.children.add(node)
        node._parent = self

    def add_value(self, value):
        if is_array(self.values):
            self.values = merge_sorted(self.values, [value])
            return
        new_values = list(self.values)
        new_values.append(value)
        new_values.sort()
        self.values = tuple(new_values)

    def add_values(self, values):
        """Add several values at once and store them as a sorted float64 array (used for longitude leaves)."""
        self.values = merge_sorted(self.values, values)

    def result_array(self):
        """This leaf's ``result`` as a float64 array, with missing values (``None``) as NaN."""
        return result_as_array(self.result)

    def prune(self, select=None, latitude_axis="latitude") -> "TensorIndexTree":
        """Return an independent copy of this (root) tree restricted to the selected field groups.

        :param select: ``{axis_name: value}`` or ``{axis_name: [value, ...]}``; on every node of each named
            axis only the listed values are kept, in the node's own order (so the compressed-axes expansion
            in ``FDBDatacube.get`` yields only those values, in tree order). Branches whose node on that
            axis holds none of them are dropped; ``ValueError`` is raised if an axis matches nothing
            anywhere in the tree. Values must compare equal to the values stored in the tree. Spatial axes
            (latitude and below) cannot be selected: a spatial sub-tree is always copied whole.
        :returns: a new tree with the same root path. Nodes are fresh objects, longitude leaf arrays are
            copied and every ``result`` is empty, so ``datacube.get`` on the pruned tree never mutates this
            tree, and several pruned trees of the same parent can be filled one after another.

        Concatenating the results of sub-trees that partition the tree's field groups reproduces the values
        and point order of a ``get`` on the unpruned tree. Pruning a tree prepared with
        ``FDBDatacube.prepare`` keeps its final point order, so a sub-tree's coordinates can be read before
        (and without) calling ``get``.
        """
        if not self.is_root():
            raise ValueError("prune() must be called on the root of a tree")
        pruned = _prune_walk(self, _prune_check_select(select, latitude_axis), latitude_axis)
        assert pruned is not None
        return pruned

    def create_merged_child(self, axes, values, next_nodes):
        node = MergedTensorIndexNode(axes, values)
        self.add_child(node)
        return (node, next_nodes)

    def create_bulk_merged_child(self, axes, coordinates, indexes, next_nodes, point_tags=None):
        node = BulkMergedTensorIndexNode(axes, coordinates, indexes, point_tags)
        existing_child = self.find_child(node)
        if existing_child is not None:
            existing_child.merge(node)
            return (existing_child, next_nodes)
        self.add_child(node)
        return (node, next_nodes)

    def create_child(self, axis, value, next_nodes):
        # TODO: what if we remove the next nodes here?
        node = TensorIndexTree(axis, (value,))
        # TODO: do we really need to find the child now in the compressed tree since we will have duplicates anyway?
        existing_child = self.find_child(node)
        if not existing_child:
            self.add_child(node)
            return (False, node, next_nodes)
        return (True, existing_child, next_nodes)

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def set_parent(self, node):
        if self.parent is not None:
            self.parent.children.remove(self)
        self._parent = node
        self._parent.children.add(self)

    def get_root(self):
        node = self
        while node.parent is not None:
            node = node.parent
        return node

    def is_root(self):
        return self.parent is None

    def find_child(self, node):
        index = self.children.bisect_left(node)
        if index < len(self.children) and self.children[index] == node:
            return self.children[index]
        return None

    def add_node_layer_after(self, ax_name, vals):
        ax = IntDatacubeAxis()
        ax.name = ax_name
        interm_node = TensorIndexTree(ax, vals)
        interm_node.children = self.children
        interm_node._parent = self
        self.children = SortedList()
        self.children.add(interm_node)
        return interm_node

    def delete_non_index_nodes(self, index_vals):
        grandparent = self._parent._parent
        grandparent.indexes.extend(index_vals)
        self.remove_branch()
        return grandparent

    def hide_non_index_nodes(self, index_vals):
        grandparent = self._parent._parent
        grandparent.indexes.extend(index_vals)
        self.hide_two_levels()
        return grandparent

    def hide_two_levels(self):
        self.hidden = True
        if self._parent.non_hidden_children() == 0:
            self._parent.hidden = True

    def non_hidden_children(self):
        non_hidden_child_counter = 0
        for c in self.children:
            if not c.hidden:
                non_hidden_child_counter += 1
        return non_hidden_child_counter

    def merge(self, other):
        self.tags.update(other.tags)
        for other_child in other.children:
            my_child = self.find_child(other_child)
            if not my_child:
                self.add_child(other_child)
            else:
                my_child.merge(other_child)

    def pprint(self, level=0):
        if self.axis.name == "root":
            logging.debug("\n")
        logging.debug("\t" * level + "\u21b3" + str(self))
        for child in self.children:
            if not child.hidden:
                child.pprint(level + 1)
        if len(self.children) == 0:
            logging.debug("\t" * (level + 1) + "\u21b3" + str(self.result))

    def remove_branch(self):
        if not self.is_root():
            old_parent = self._parent
            self._parent.children.remove(self)
            self._parent = None
            if len(old_parent.children) == 0:
                old_parent.remove_branch()

    def remove_compressed_branch(self, value):
        if value not in self.values:
            return

        if len(self.values) == 1:
            self.remove_branch()
            return

        self.values = remove_value(self.values, value)
        parent = self.parent
        if parent is None:
            return

        for sibling in parent.children:
            if sibling is not self:
                if self == sibling:
                    self.remove_branch()
                    return

    def flatten(self):
        path = DatacubePath()
        ancestors = self.get_ancestors()
        for ancestor in ancestors:
            path[ancestor.axis.name] = ancestor.values
        return path

    def get_ancestors(self):
        ancestors = []
        current_node = self
        while current_node.axis.name != "root":
            ancestors.append(current_node)
            current_node = current_node.parent
        return ancestors[::-1]


# ---------------------------------------------------------------------------
# TensorIndexTree.prune(): depth-first copy of the branches matching a value selection, restricted
# to a value -- or set of values -- on each compressed non-spatial axis (date/time/step/number/
# param/levelist...). See TensorIndexTree.prune's docstring for the full contract.
#
# A caller slices a request once, then repeatedly prunes the tree and calls ``datacube.get`` on each
# pruned tree.  The pruned trees share no mutable state with the parent, so ``get`` (which reorders
# and de-duplicates leaf values and fills ``result``) never touches the parent tree.  Calling
# ``FDBDatacube.prepare`` on the parent first puts its points into their final (``get``) order, so
# every pruned sub-tree's coordinates are known before any data is fetched.
# ---------------------------------------------------------------------------


def _prune_value_matches(node_value, wanted, axis):
    try:
        if node_value == wanted:
            return True
    except (TypeError, ValueError):
        return False
    if getattr(axis, "can_round", False) and isinstance(node_value, (int, float, np.number)):
        try:
            return abs(node_value - wanted) <= 2 * axis.tol
        except TypeError:
            return False
    return False


def _prune_wanted_values(wanted):
    """``wanted`` as a sequence of values: one value selects itself."""
    if isinstance(wanted, (list, tuple, set, frozenset, np.ndarray)):
        return list(wanted)
    return [wanted]


def _prune_select_values(node, wanted):
    """``(values, hits)``: the elements of ``node.values`` matching ``wanted`` and which of ``wanted`` matched.

    ``wanted`` is one value or a sequence of them.  The values are the tree's own objects in the node's order,
    so the compressed-axes expansion of ``FDBDatacube.get`` stays in tree order; ``hits`` are positions in
    ``wanted``, so that a value the tree does not have anywhere can be named.
    """
    choices = _prune_wanted_values(wanted)
    values = []
    hits = set()
    for v in node.values:
        for i, w in enumerate(choices):
            if _prune_value_matches(v, w, node.axis):
                values.append(v)
                hits.add(i)
                break
    return tuple(values), hits


def _prune_copy_node(node, values=None):
    new = TensorIndexTree(node.axis, node.values if values is None else values)
    if isinstance(new.values, np.ndarray):
        new.values = new.values.copy()
    new.indexes = list(node.indexes)
    new.hidden = node.hidden
    new.tags = set(node.tags)
    if node._keep_value_order:
        new._keep_value_order = True
    if node.tag_ids is not None and values is None:
        # per-point tags of an array leaf: shared, not copied per point
        new.tag_sets = node.tag_sets
        new.tag_ids = node.tag_ids
    return new


def _prune_copy_merged(node):
    new = MergedTensorIndexNode(node.axes, node.values)
    new.indexes = list(node.indexes)
    new.hidden = node.hidden
    new.tags = set(node.tags)
    return new


def _prune_copy_subtree(node):
    if isinstance(node, BulkMergedTensorIndexNode):
        # share the node's arrays: a bulk node holds the whole spatial selection
        return node.copy_shared()
    if isinstance(node, MergedTensorIndexNode):
        return _prune_copy_merged(node)
    new = _prune_copy_node(node)
    for child in node.children:
        new.add_child(_prune_copy_subtree(child))
    return new


def _prune_check_select(select, latitude_axis):
    select = dict(select or {})
    for name in select:
        if name in (latitude_axis, "longitude"):
            raise ValueError(f"Cannot select on spatial axis {name!r}")
    return select


def _prune_walk(root, select, latitude_axis):
    """Depth-first copy of the branches matching ``select``; spatial sub-trees are copied whole."""
    matched: dict = {}

    def visit(src, dst):
        kept_any = False
        for child in src.children:
            if isinstance(child, MergedTensorIndexNode) or child.axis.name == latitude_axis:
                dst.add_child(_prune_copy_subtree(child))
                kept_any = True
                continue
            values = None
            name = child.axis.name
            if name in select:
                values, hits = _prune_select_values(child, select[name])
                if not values:
                    continue
                matched.setdefault(name, set()).update(hits)
            new = _prune_copy_node(child, values)
            if len(child.children) == 0:
                # leaf above the latitude level (non-spatial tree): keep it whole
                dst.add_child(new)
                kept_any = True
                continue
            if visit(child, new):
                dst.add_child(new)
                kept_any = True
        return kept_any

    new_root = _prune_copy_node(root)
    visit(root, new_root)
    missing = {}
    for name, wanted in select.items():
        hits = matched.get(name, ())
        absent = [w for i, w in enumerate(_prune_wanted_values(wanted)) if i not in hits]
        if absent:
            missing[name] = absent
    if missing:
        raise ValueError(
            "Values not found in tree: "
            + ", ".join(
                f"{name}={values[0]!r}" if len(values) == 1 else f"{name}={values!r}"
                for name, values in sorted(missing.items())
            )
        )
    return new_root


# ---------------------------------------------------------------------------
# RowMerger: one longitude leaf per latitude node for unions of non-orthogonal shapes (polygons, paths).
#
# A polygon is sliced as a union of convex pieces (triangles), each into its own tree, and the trees are merged.
# Without RowMerger the leaf (longitude) axis is left uncompressed for such unions, so that merging
# de-duplicates the points shared by neighbouring pieces, at the cost of one tree node per point (~1.4 KB/point).
# With RowMerger the leaf axis stays compressed: each piece gives one float64 leaf per latitude node, and
# merging concatenates the leaves under the same latitude node into one sorted, de-duplicated array.
#
# The merged leaf holds exactly the points, in the same (ascending) order, as the per-point leaves did.  Its
# ``_keep_value_order`` flag tells ``FDBDatacube.get``/``prepare`` to keep that order instead of reordering the
# values by grid index, as they do for box leaves (on HEALPix nested grids the two orders differ), so results come
# out in the order the per-point leaves gave.
#
# Each piece's leaf carries that piece's tag, so a union of differently tagged shapes (several polygons, several
# tagged Points on a structured grid) would lose information if the merged leaf carried one set of tags for all of
# its points.  The merged leaf therefore gets per-point tags (``set_point_tags``) whenever its pieces disagree, and
# a point selected by several pieces carries the union of their tags; this is what lets such unions stay compressed
# instead of falling back to one node per point.
# ---------------------------------------------------------------------------


def _row_merge_is_array_leaf(node, leaf_axis_name):
    return node.axis.name == leaf_axis_name and len(node.children) == 0 and is_array(node.values)


def _row_merge_piece_tag_ids(pieces):
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


def _row_merge_union_duplicate_tags(values, tag_sets, tag_ids):
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
            if _row_merge_is_array_leaf(child, self.leaf_axis_name):
                my_leaf = child
                break
        for other_child in list(other.children):
            if _row_merge_is_array_leaf(other_child, self.leaf_axis_name):
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
            tag_sets, piece_ids = _row_merge_piece_tag_ids(pieces)
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
                if _row_merge_is_array_leaf(child, self.leaf_axis_name):
                    child._keep_value_order = True
                    values = child.values
                    if len(values) > 1 and bool(np.any(values[1:] == values[:-1])):
                        # several pieces (or cyclic copies of one piece) gave the same point: keep it once
                        node.children.remove(child)
                        if child.tag_ids is None:
                            child.values = np.unique(values)
                        else:
                            unique, tag_sets, tag_ids = _row_merge_union_duplicate_tags(
                                values, child.tag_sets, child.tag_ids
                            )
                            child.values = unique
                            child.set_point_tags(tag_sets, tag_ids)
                        node.add_child(child)
                elif len(child.children) != 0:
                    stack.append(child)
        return tree
