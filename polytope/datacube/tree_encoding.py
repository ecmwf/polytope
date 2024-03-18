import numpy as np
import pandas as pd

from . import index_tree_pb2 as pb2
from .datacube_axis import IntDatacubeAxis
from .index_tree import IndexTree


def encode_tree(tree: IndexTree):
    node = pb2.Node()

    node.axis = tree.axis.name
    if tree.result is not None:
        node.result = tree.result

    # Assign the node value according to the type
    # Argueably, do not need to do this since we will only encode from the root node...
    if isinstance(tree.value, int):
        node.int_val = tree.value
    if isinstance(tree.value, float):
        node.double_val = tree.value
    if isinstance(tree.value, str):
        node.str_val = tree.value
    if isinstance(tree.value, pd.Timestamp):
        node.str_val = tree.value.strftime("%Y/%m/%dT%H:%M:%S")
    if isinstance(tree.value, np.datetime64):
        node.str_val = pd.to_datetime(str(tree.value)).strftime("%Y/%m/%dT%H:%M:%S")
    if isinstance(tree.value, np.timedelta64):
        node.str_val = str(tree.value)

    # Nest children in protobuf root tree node
    for c in tree.children:
        encode_child(tree, c, node)

    # Write to file
    with open("./serializedTree", "wb") as fd:
        fd.write(node.SerializeToString())


# TODO: complete the type mappings to the right value protobuf attribute and use as a factory?
# type_mappings = {int: "int_val",
#                  str: "str_val",
#                  float: "double_val"}


def encode_child(tree: IndexTree, child: IndexTree, node):
    child_node = pb2.Node()

    child_node.axis = child.axis.name
    if child.result is not None:
        child_node.result = child.result

    # Assign the node value according to the type
    if isinstance(child.value, int):
        child_node.int_val = child.value
    if isinstance(child.value, float):
        child_node.double_val = child.value
    if isinstance(child.value, str):
        child_node.str_val = child.value
    if isinstance(child.value, pd.Timestamp):
        child_node.str_val = child.value.strftime("%Y%m%dT%H%M%S")
    if isinstance(child.value, np.datetime64):
        child_node.str_val = pd.to_datetime(str(child.value)).strftime("%Y/%m/%dT%H:%M:%S")
    if isinstance(child.value, np.timedelta64):
        child_node.str_val = str(child.value)

    for c in child.children:
        encode_child(child, c, child_node)

    # NOTE: we append the children once their branch has been completed until the leaf
    node.children.append(child_node)


def decode_tree(datacube):
    node = pb2.Node()
    with open("./serializedTree", "rb") as f:
        node.ParseFromString(f.read())

    tree = IndexTree()

    if node.axis == "root":
        root = IntDatacubeAxis()
        root.name = "root"
        tree.axis = root
    else:
        tree.axis = datacube._axes[node.axis]

    # Put contents of node children into tree
    decode_child(node, tree, datacube)

    return tree


def decode_child(node, tree, datacube):
    if len(node.children) == 0:
        tree.result = node.result
    for child in node.children:
        child_axis = datacube._axes[child.axis]
        child_val = getattr(child, child.WhichOneof("value"))
        child_node = IndexTree(child_axis, child_val)
        tree.add_child(child_node)
        decode_child(child, child_node, datacube)
