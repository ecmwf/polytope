import numpy as np
import pandas as pd

from . import index_tree_pb2 as pb2
from .datacube_axis import IntDatacubeAxis
from .tensor_index_tree import TensorIndexTree


def encode_tree(tree: TensorIndexTree):
    node = pb2.Node()

    node.axis = tree.axis.name

    # NOTE: do we need this if we parse the tree before it has values?
    if tree.result is not None:
        for result in tree.result:
            node.result.append(result)

    # Assign the node value according to the type
    # Argueably, do not need to do this since we will only encode from the root node...
    # if isinstance(tree.value[0], int):
    #     for i, tree_val in enumerate(tree.value):
    #         node.value[i].int_val = tree_val
    # if isinstance(tree.value[0], float):
    #     for i, tree_val in enumerate(tree.value):
    #         node.value[i].double_val = tree_val
    # if isinstance(tree.value[0], str):
    #     for i, tree_val in enumerate(tree.value):
    #         node.value[i].str_val = tree_val
    # if isinstance(tree.value[0], pd.Timestamp):
    #     for i, tree_val in enumerate(tree.value):
    #         node.value[i].str_val = tree_val.strftime("%Y/%m/%dT%H:%M:%S")
    # if isinstance(tree.value[0], np.datetime64):
    #     for i, tree_val in enumerate(tree.value):
    #         node.value[i].str_val = pd.to_datetime(str(tree_val)).strftime("%Y/%m/%dT%H:%M:%S")
    # if isinstance(tree.value[0], np.timedelta64):
    #     for i, tree_val in enumerate(tree.value):
    #         node.value[i].str_val = str(tree_val)

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


def encode_child(tree: TensorIndexTree, child: TensorIndexTree, node, result_size=[]):
    child_node = pb2.Node()

    child_node.axis = child.axis.name
    result_size.append(len(child.values))

    # Add the result size to the final node
    # TODO: how to assign repeated fields more efficiently?
    # NOTE: this will only really be efficient when we compress and have less leaves
    if len(child.children) == 0:
        child_node.result_size.extend(result_size)
    # NOTE: do we need this if we parse the tree before it has values?
    # TODO: not clear if child.value is a numpy array or a simple float...
    # TODO: not clear what happens if child.value is a np array since this is not a supported type by protobuf
    if child.result is not None:
        if isinstance(child.result, list):
            for result in child.result:
                child_node.result.append(result)
        else:
            child_node.result.append(child.result)

    # Assign the node value according to the type
    if isinstance(child.values[0], int):
        for i, child_val in enumerate(child.values):
            child_node_val = pb2.Value()
            child_node_val.int_val = child_val
            child_node.value.append(child_node_val)
    if isinstance(child.values[0], float):
        for i, child_val in enumerate(child.values):
            child_node_val = pb2.Value()
            child_node_val.double_val = child_val
            child_node.value.append(child_node_val)
    if isinstance(child.values[0], str):
        for i, child_val in enumerate(child.values):
            child_node_val = pb2.Value()
            child_node_val.str_val = child_val
            child_node.value.append(child_node_val)
    if isinstance(child.values[0], pd.Timestamp):
        for i, child_val in enumerate(child.values):
            child_node_val = pb2.Value()
            child_node_val.str_val = child_val.strftime("%Y%m%dT%H%M%S")
            child_node.value.append(child_node_val)
    if isinstance(child.values[0], np.datetime64):
        for i, child_val in enumerate(child.values):
            child_node_val = pb2.Value()
            child_node_val.str_val = pd.to_datetime(str(child_val)).strftime("%Y/%m/%dT%H:%M:%S")
            child_node.value.append(child_node_val)
    if isinstance(child.values[0], np.timedelta64):
        for i, child_val in enumerate(child.values):
            child_node_val = pb2.Value()
            child_node_val.str_val = str(child_val)
            child_node.value.append(child_node_val)

    for c in child.children:
        result_size.append(len(child.values))
        encode_child(child, c, child_node, result_size)

    # NOTE: we append the children once their branch has been completed until the leaf
    node.children.append(child_node)


def decode_tree(datacube):
    node = pb2.Node()
    with open("./serializedTree", "rb") as f:
        node.ParseFromString(f.read())

    tree = TensorIndexTree()

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
        tree.result_size = node.result_size
    for child in node.children:
        child_axis = datacube._axes[child.axis]
        child_vals = []
        for child_val in child.value:
            child_vals.append(getattr(child_val, child_val.WhichOneof("value")))
        child_vals = tuple(child_vals)
        child_node = TensorIndexTree(child_axis, child_vals)
        tree.add_child(child_node)
        decode_child(child, child_node, datacube)
