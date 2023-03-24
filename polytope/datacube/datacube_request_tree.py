from sortedcontainers import SortedList
from typing import OrderedDict
import json

from .datacube_axis import IntAxis

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


class DatacubeRequestTree(object):

    root = IntAxis()
    root.name = "root"

    def __init__(self, axis=root, value=None):
        self.value = value 
        self.children = SortedList()
        self._parent = None
        self.result = None
        self.axis = axis

    @property
    def leaves(self):
        leaves = []
        self._collect_leaf_nodes(leaves)
        return leaves

    def _collect_leaf_nodes(self, leaves):
        if len(self.children) == 0:
            leaves.append(self)
        for n in self.children:
            n._collect_leaf_nodes(leaves)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __getitem__(self, key):
        return getattr(self, key)

    def __delitem__(self, key):
        return delattr(self, key)

    def __hash__(self):
        return hash((self.axis.name, self.value))
    
    def __eq__(self, other):
        if not isinstance(other, DatacubeRequestTree):
            return False
        return (self.axis.name, self.value) == (other.axis.name, other.value)
    
    def __lt__(self, other):
        return (self.axis.name, self.value) < (other.axis.name, other.value)

    def __repr__(self):
        if self.axis != "root":
            return f"{self.axis.name}={self.value}"
        else:
            return f"{self.axis}"

    def add_child(self, node):
        self.children.add(node)
        node._parent = self

    def create_child(self, axis, value):
        node = DatacubeRequestTree(axis, value)
        self.add_child(node)
        return node

    def create_child_safe(self, axis, value):
        node = DatacubeRequestTree(axis, value)
        existing = self.find_child(node)
        if not existing:
            self.add_child(node)
            return node
        return existing

    @property 
    def parent(self):
        return self._parent
    
    @parent.setter
    def set_parent(self, node):
        if self.parent != None:
            self.parent.children.remove(self)
        self._parent = node
        self._parent.children.add(self)


    def get_root(self):
        node = self
        while node.parent != None:
            node = node.parent
        return node

    def is_root(self):
        return self.parent == None
    
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


    def intersect(self, other):
        for my_child in self.children:
            other_child = other.find_child(my_child)
            if not other_child:
                my_child.remove_branch()
            else:
                my_child.intersect(other_child)


    def pprint(self, level=0):
        if self.axis == "root":
            print("\n")
        print("\t"*level + "\u21b3" + str(self))
        for child in self.children:
            child.pprint(level+1)


    def remove_branch(self):
        if not self.is_root():
            old_parent = self._parent
            self._parent.children.remove(self)
            self._parent = None
            if len(old_parent.children) == 0:
                old_parent.remove_branch()

    def flatten(self):
        path = DatacubePath()
        ancestors = self.get_ancestors()
        for ancestor in ancestors:
            path[ancestor.axis.name] = ancestor.value
        return path

    def get_ancestors(self):
        ancestors = []
        current_node = self
        while current_node.axis != DatacubeRequestTree.root:
            ancestors.append(current_node)
            current_node = current_node.parent
        return ancestors[::-1]


    def to_dict(self):
        dico = dict()
        if self.children != []:
            # Need to create these lists in case different children have different axis and we need to give values to each axis
            axis_names = [c.axis.name for c in self.children]
            sub_dicts = [dict() for axis in axis_names]
            for i in range(len(axis_names)):
                dico[axis_names[i]] = sub_dicts[i]
            for c in self.children:
                key = c.axis.serialize(c.value)
                axis_name = c.axis.name
                dico[axis_name][key] = c.to_dict()
        if self.children == []:
                return self.result
        return dico



    def to_json(self):
        dico = self.to_dict()
        return json.dumps(dico, default=str)



