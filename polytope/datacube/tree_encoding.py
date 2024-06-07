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


def encode_child(tree: TensorIndexTree, child: TensorIndexTree, node, result_size=[]):
    child_node = pb2.Node()

    new_result_size = deepcopy(result_size)
    new_result_size.append(len(child.values))

    # Add the result size to the final node
    # TODO: how to assign repeated fields more efficiently?
    # NOTE: this will only really be efficient when we compress and have less leaves
    # if len(child.children) == 0:
    #     # TODO: here, we need to find the last node which isn't hidden and add all of this to that one
    #     result_size.append(len(child.values))
    #     # result_size.append(len(child.indexes))
    #     child_node.size_result.extend(result_size)
    #     child_node.indexes.extend(child.indexes)

    # if len(child.children) != 0:
    #     if len(child.children[0].children) == 0:
    #         # NOTE: here we are with tree is the grandparent so need to add everything to it, including the size_index
    #     result_size.append(len(child.values))
    #     # result_size.append(len(child.indexes))
    #     child_node.size_result.extend(result_size)
    #     child_node.indexes.extend(child.indexes)

    if child.hidden:
        # add indexes to parent and add also indexes size...
        node.indexes.extend(tree.indexes)
        node.size_indexes_branch.append(len(child.children))
        # node.size_result.extend(result_size)


    # TODO: need to add axis and children etc to the encoded node only if the tree node isn't hidden 
    else:
        child_node.axis = child.axis.name
        child_node.value.extend(child.values)
        child_node.size_result.extend(new_result_size)

    # NOTE: do we need this if we parse the tree before it has values?
    # TODO: not clear if child.value is a numpy array or a simple float...
    # TODO: not clear what happens if child.value is a np array since this is not a supported type by protobuf
    # if child.result is not None:
    #     if isinstance(child.result, list):
    #         child_node.result.extend(child.result)
    #     else:
    #         child_node.result.append(child.result)

    # Assign the node value according to the type
    # child_node.value.extend(child.values)
    # for child_val in child.values:
    #     child_node.value.append(child_val)

    for c in child.children:
        # new_result_size = deepcopy(result_size)
        # new_result_size.append(len(child.values))
        encode_child(child, c, child_node, new_result_size)

    # NOTE: we append the children once their branch has been completed until the leaf
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
