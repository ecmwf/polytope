import copy
import logging

from sortedcontainers import SortedList

from .datacube_axis import IntDatacubeAxis, UnsliceableDatacubeAxis
from .index_tree import DatacubePath


class TensorIndexTree(object):
    root = IntDatacubeAxis()
    root.name = "root"

    def __init__(self, axis=root, values=tuple()):
        # NOTE: the values here is a tuple so we can hash it
        self.values = values
        self.children = SortedList()
        self._parent = None
        self.result = None
        self.axis = axis
        self.ancestors = []

    @property
    def leaves(self):
        leaves = []
        self._collect_leaf_nodes(leaves)
        return leaves

    @property
    def leaves_with_ancestors(self):
        leaves = []
        self._collect_leaf_nodes(leaves)
        return leaves

    def copy_children_from_other(self, other):
        for o in other.children:
            c = TensorIndexTree(o.axis, copy.copy(o.value))
            self.add_child(c)
            c.copy_children_from_other(o)
        return

    def _collect_leaf_nodes(self, leaves):
        # NOTE: leaves_and_ancestors is going to be a list of tuples, where first entry is leaf and second entry is a
        # list of its ancestors
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
                        if abs(other_val - self_val) > 2 * max(other.axis.tol, self.axis.tol):
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

    def find_compressed_child(self, axis):
        for c in self.children:
            if c.axis == axis:
                return c
        return None

    def create_child(self, axis, value, compressed_axes, next_nodes):
        # TODO: if the axis should not be compressed, just create a child with a tuple value with a single value
        # TODO: if the axis should be compressed, check if we already have a child with the axis name.
        # TODO: Then: if we have such a child, add to its tuple value the new value.
        # TODO: Else, just create a child with a tuple value with a single value
        # logging.debug("inside create child")
        # logging.debug(value)
        if axis.name not in compressed_axes:
            # In this case, the child should not already exist? But you never know if the slicer hasn't found the same value twice? It shouldn't though?
            # Can safely add the child here though to self
            node = TensorIndexTree(axis, (value,))
            existing_child = self.find_child(node)
            if not existing_child:
                self.add_child(node)
                return (node, next_nodes)
            # next_nodes.remove(existing_child)
            return (existing_child, next_nodes)
        else:
            # TODO: find the compressed child
            existing_compressed_child = self.find_compressed_child(axis)
            # logging.debug("HERE?")
            # logging.debug(existing_compressed_child)
            # logging.debug(next_nodes)
            if existing_compressed_child:
                # NOTE: do we even need to hash the values anymore if we implement logic to only compare children when
                # we have the right compressed children? Then could have a list here for the values which is easier to
                # manipulate...
                new_value = list(existing_compressed_child.values)
                new_value.append(value)
                existing_compressed_child.values = tuple(new_value)
                next_nodes.remove(existing_compressed_child)
                # logging.debug("HERE?")
                # logging.debug(existing_compressed_child)
                # logging.debug(next_nodes)
                return (existing_compressed_child, next_nodes)
            else:
                node = TensorIndexTree(axis, (value,))
                self.add_child(node)
                return (node, next_nodes)

        # node = TensorIndexTree(axis, value)
        # existing = self.find_child(node)
        # if not existing:
        #     self.add_child(node)
        #     return node
        # return existing

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
        if index >= len(self.children):
            return None
        child = self.children[index]
        if not child == node:
            return None
        return child

    def merge(self, other):
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
        if value in self.values:
            if len(self.values) == 1:
                self.remove_branch()
            else:
                self.values = tuple(val for val in self.values if val != value)

    def flatten(self):
        path = DatacubePath()
        ancestors = self.get_ancestors()
        for ancestor in ancestors:
            path[ancestor.axis.name] = ancestor.values
        return path

    def flatten_with_ancestors(self):
        path = DatacubePath()
        ancestors = self.ancestors
        for ancestor in ancestors:
            path[ancestor.axis.name] = ancestor.values
        return path

    def get_ancestors(self):
        ancestors = []
        current_node = self
        while current_node.axis != TensorIndexTree.root:
            ancestors.append(current_node)
            current_node = current_node.parent
        return ancestors[::-1]
