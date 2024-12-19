import math
from copy import deepcopy

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

    # Nest children in protobuf root tree node
    for c in tree.children:
        encode_child(tree, c, node)

    # Write to file
    return node.SerializeToString()


def write_encoded_tree_to_file(tree_bytes):
    with open("encodedTree", "wb") as fs:
        fs.write(tree_bytes)


def encode_child(tree: TensorIndexTree, child: TensorIndexTree, node, result_size=[]):
    child_node = pb2.Node()

    new_result_size = deepcopy(result_size)
    # new_result_size = result_size
    new_result_size.append(len(child.values))

    if child.hidden:
        # add indexes to parent and add also indexes size...
        node.indexes.extend(tree.indexes)
        break_tag = False
        return break_tag

    # need to add axis and children etc to the encoded node only if the tree node isn't hidden
    else:
        child_node.axis = child.axis.name
        child_node.value.extend(child.values)
        child_node.size_result.extend(new_result_size)

        for c in child.children:
            breaking = encode_child(child, c, child_node, new_result_size)
            if not breaking:
                for c_ in child.children:
                    child_node.size_indexes_branch.append(len(c_.children))
                break

        # we append the children once their branch has been completed until the leaf
        if not child.hidden:
            node.children.append(child_node)


def decode_tree(datacube, bytearray):
    node = pb2.Node()
    node.ParseFromString(bytearray)

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
        tree.result_size = node.size_result
        tree.indexes = node.indexes
        tree.indexes_size = node.size_indexes_branch
    for child in node.children:
        if child.axis in datacube._axes.keys():
            child_axis = datacube._axes[child.axis]
            child_vals = tuple(child.value)
            child_node = TensorIndexTree(child_axis, child_vals)
            tree.add_child(child_node)
            decode_child(child, child_node, datacube)
        else:
            grandchild_axis = datacube._axes[child.children[0].axis]
            for c in child.children:
                grandchild_vals = tuple(c.value)
                grandchild_node = TensorIndexTree(grandchild_axis, grandchild_vals)
                tree.add_child(grandchild_node)
                decode_child(c, grandchild_node, datacube)


def decode_into_tree(tree, bytearray):
    # TODO: write a decoder that decodes the bytearray (ie results) from gribjump directly into the tree instance
    node = pb2.Node()
    node.ParseFromString(bytearray)

    decode_child_into_tree(tree, node)

    return tree


def decode_child_into_tree(tree, node):
    if not tree.hidden:
        # iterate through tree
        for i, child in enumerate(tree.children):
            node_c = node.children[i]
            decode_child_into_tree(child, node_c)
    else:
        # TODO: if it's hidden, use the sizes to attribute to the hidden lat/lon nodes...
        num_results = math.prod(node.size_result)
        num_lat_branches = len(tree.children)
        start_result_idx = 0
        for i in range(num_lat_branches):
            lat_node = tree.children[i]
            num_lon_branches = len(lat_node.children)
            for j in range(num_lon_branches):
                lon_node = lat_node.children[j]
                next_result_idx = start_result_idx + num_results
                lon_node.result = node.result[start_result_idx:next_result_idx]
                start_result_idx = next_result_idx
