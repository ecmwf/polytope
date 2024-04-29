import capnp
import numpy as np
import pandas as pd

from .datacube_axis import IntDatacubeAxis
from .tensor_index_tree import TensorIndexTree

tree_obj = capnp.load('indexTree.capnp')


def encode_tree(tree: TensorIndexTree):
    node = tree_obj.Node.new_message()

    node.axis = tree.axis.name

    # NOTE: do we need this if we parse the tree before it has values?
    if tree.result is not None:
        for result in tree.result:
            node.result.append(result)

    # Nest children in protobuf root tree node
    for i, c in enumerate(tree.children):
        children = node.init("children", int(len(tree.children)))
        encode_child(tree, c, i, node, children)

    # Write to file
    # node.write("./serializedTree")
    with open("./serializedTree", "wb") as fd:
        fd.write(node.to_bytes())


def encode_child(tree: TensorIndexTree, child: TensorIndexTree, i, node, children, result_size=[]):
    child_node = tree_obj.Node.new_message()
    values = child_node.init('value', int(len(child.values)))

    child_node.axis = child.axis.name
    result_size.append(len(child.values))

    # Add the result size to the final node
    # TODO: how to assign repeated fields more efficiently?
    # NOTE: this will only really be efficient when we compress and have less leaves
    if len(child.children) == 0:
        # child_node.resultSize.extend(result_size)
        child_node.resultSize = result_size
    
    # NOTE: do we need this if we parse the tree before it has values?
    # TODO: not clear if child.value is a numpy array or a simple float...
    # TODO: not clear what happens if child.value is a np array since this is not a supported type by protobuf
    if child.result is not None:
        if isinstance(child.result, list):
            # for result in child.result:
            #     child_node.result.append(result)
            child_node.result = child.result
        else:
            # child_node.result.append(child.result)
            child_node.result = [float(child.result)]

    # Assign the node value according to the type
    if isinstance(child.values[0], int):
        for j, child_val in enumerate(child.values):
            child_node_val = tree_obj.Value.new_message()
            child_node_val.value.intVal = child_val
            # child_node.value.append(child_node_val)
            values[j] = child_node_val
    if isinstance(child.values[0], float):
        for j, child_val in enumerate(child.values):
            child_node_val = tree_obj.Value.new_message()
            child_node_val.value.doubleVal = child_val
            # child_node.value.append(child_node_val)
            values[j] = child_node_val
    if isinstance(child.values[0], str):
        for j, child_val in enumerate(child.values):
            child_node_val = tree_obj.Value.new_message()
            child_node_val.value.strVal = child_val
            # child_node.value.append(child_node_val)
            values[j] = child_node_val
    if isinstance(child.values[0], pd.Timestamp):
        for j, child_val in enumerate(child.values):
            child_node_val = tree_obj.Value.new_message()
            child_node_val.value.strVal = child_val.strftime("%Y%m%dT%H%M%S")
            # child_node.value.append(child_node_val)
            values[j] = child_node_val
    if isinstance(child.values[0], np.datetime64):
        for j, child_val in enumerate(child.values):
            child_node_val = tree_obj.Value.new_message()
            child_node_val.value.strVal = pd.to_datetime(str(child_val)).strftime("%Y/%m/%dT%H:%M:%S")
            # child_node.value.append(child_node_val)
            values[j] = child_node_val
    if isinstance(child.values[0], np.timedelta64):
        for j, child_val in enumerate(child.values):
            child_node_val = tree_obj.Value.new_message()
            child_node_val.value.strVal = str(child_val)
            # child_node.value.append(child_node_val)
            values[j] = child_node_val

    for k, c in enumerate(child.children):
        result_size.append(len(child.values))
        child_children = child_node.init("children", int(len(child.children)))
        encode_child(child, c, k, child_node, child_children, result_size)

    # NOTE: we append the children once their branch has been completed until the leaf
    # node.children.append(child_node)
    children[i] = child_node


def decode_tree(datacube):
    node = tree_obj.Node.read("./serializedTree")
    # with open("./serializedTree", "rb") as f:
    #     node.ParseFromString(f.read())

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
        tree.result_size = node.resultSize
    for child in node.children:
        child_axis = datacube._axes[child.axis]
        child_vals = []
        for child_val in child.value:
            child_vals.append(getattr(child_val, child_val.WhichOneof("value")))
        child_vals = tuple(child_vals)
        child_node = TensorIndexTree(child_axis, child_vals)
        tree.add_child(child_node)
        decode_child(child, child_node, datacube)
