import logging
from typing import OrderedDict

import numpy as np
from sortedcontainers import SortedList

from .datacube_axis import IntDatacubeAxis, UnsliceableDatacubeAxis


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

    At most one bulk node exists per parent: bulk nodes on the same axes compare
    equal, so merging trees (eg. for unions) unions their points instead of
    adding siblings.
    """

    def __init__(self, axes, coordinates, indexes):
        super().__init__(axes, ())
        self.coordinates = np.asarray(coordinates, dtype=np.float64).reshape(-1, 2)
        self.indexes = None if indexes is None else np.asarray(indexes, dtype=np.int64)

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
        _, first = np.unique(indexes, return_index=True)
        coordinates = coordinates[first]
        indexes = indexes[first]
        order = np.lexsort((coordinates[:, 1], coordinates[:, 0]))
        self.coordinates = coordinates[order]
        self.indexes = indexes[order]


class BulkGridTensorIndexNode(BulkMergedTensorIndexNode):
    """Array-backed leaf for a structured (hullslicer) lat/lon selection.

    Replaces the ``latitude -> longitude`` layers under one path: ``lat_values``
    holds the selected latitudes and ``lon_values[i]`` the (compressed)
    longitudes selected on latitude ``i``. The points, and so ``coordinates``,
    ``indexes`` and each ``result`` array, are ordered latitude-major, with the
    points of row ``i`` at ``row_slice(i)``.
    """

    def __init__(self, axes, lat_values, lon_values, indexes=None):
        self.lat_values = np.asarray(lat_values, dtype=np.float64)
        self.lon_values = [np.asarray(lons, dtype=np.float64) for lons in lon_values]
        row_lengths = np.array([len(lons) for lons in self.lon_values], dtype=np.int64)
        self.row_offsets = np.concatenate([[0], np.cumsum(row_lengths)])
        if len(self.lon_values) == 0:
            coordinates = np.empty((0, 2))
        else:
            coordinates = np.column_stack((np.repeat(self.lat_values, row_lengths), np.concatenate(self.lon_values)))
        super().__init__(axes, coordinates, indexes)

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

    def __init__(self, axis=root, values=tuple()):
        # NOTE: the values here is a tuple so we can hash it
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
        return hash((self.axis.name, self.values))

    def __eq__(self, other):
        if not isinstance(other, TensorIndexTree):
            return False
        if self.axis.name != other.axis.name:
            return False
        else:
            if other.values == self.values:
                return True
            else:
                if isinstance(self.axis, UnsliceableDatacubeAxis):
                    return False
                else:
                    if len(other.values) != len(self.values):
                        return False
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
        return (self.axis.name, self.values) < (other.axis.name, other.values)

    def __repr__(self):
        if self.axis != "root":
            return f"{self.axis.name}={self.values}"
        else:
            return f"{self.axis}"

    def add_child(self, node):
        self.children.add(node)
        node._parent = self

    def add_value(self, value):
        new_values = list(self.values)
        new_values.append(value)
        new_values.sort()
        self.values = tuple(new_values)

    def create_merged_child(self, axes, values, next_nodes):
        node = MergedTensorIndexNode(axes, values)
        self.add_child(node)
        return (node, next_nodes)

    def create_bulk_merged_child(self, axes, coordinates, indexes, next_nodes):
        node = BulkMergedTensorIndexNode(axes, coordinates, indexes)
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

        self.values = tuple(val for val in self.values if val != value)
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
