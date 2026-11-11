import logging
from copy import copy
from typing import Optional, OrderedDict

import numpy as np
from sortedcontainers import SortedList

from .datacube_axis import IntDatacubeAxis, UnsliceableDatacubeAxis
from .tree_values import (
    is_array,
    merge_sorted,
    remove_value,
    result_as_array,
    values_hash_key,
    values_identical,
    values_lt,
    values_within_tol,
)


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
    # Set on the merged longitude leaves of polygons/paths (see tree_rows.py): FDBDatacube.get keeps their values in
    # ascending order instead of reordering them by grid index.
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
        # slicer hold a float64 np.ndarray instead; see tree_values.py for the shared comparison semantics.
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
        from .tree_pruning import prune

        return prune(self, select, latitude_axis)

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
