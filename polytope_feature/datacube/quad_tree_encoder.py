import math
from copy import deepcopy

from . import quad_tree_pb2 as pb2
from .quad_tree import QuadTree, QuadNode


# Encoding


def encode_tree(tree: QuadTree):
    node = pb2.QuadTree()

    node.depth = 0

    for coord in tree.center:
        node.center.append(coord)

    for size in tree.size:
        node.size.append(size)

    # if len(tree.nodes) != 0:
    for quad_node in tree.nodes:
        encoded_node = encode_quad_node(quad_node)
        node.nodes.append(encoded_node)

    # if len(tree.children) != 0:
    for node_child in tree.children:
        encode_child(node_child, node)

    # Get bytestring
    return node.SerializeToString()


def encode_child(child: QuadTree, pb2_node):
    child_node = pb2.QuadTree()
    child_node.depth = child.depth

    for coord in child.center:
        child_node.center.append(coord)

    for size in child.size:
        child_node.size.append(size)

    # if len(child.nodes) != 0:
    for quad_node in child.nodes:
        encoded_node = encode_quad_node(quad_node)
        child_node.nodes.append(encoded_node)

    for c in child.children:
        encode_child(c, child_node)

    pb2_node.children.append(child_node)


def encode_quad_node(quad_node: QuadNode):
    node = pb2.QuadNode()

    for i in quad_node.item:
        node.item.append(i)

    node.index = quad_node.index
    return node


def write_encoded_tree_to_file(tree_bytes, filename):
    with open(filename, "wb") as fs:
        fs.write(tree_bytes)


# Decoding

def decode_quad_node(pb2_quad_node):
    node = QuadNode(pb2_quad_node.item, pb2_quad_node.index)
    return node


def decode_quad_tree(bytearray):
    node = pb2.QuadTree()
    node.ParseFromString(bytearray)

    tree = QuadTree(node.center[0], node.center[1], node.size, node.depth)

    for n in node.nodes:
        decoded_node = decode_quad_node(n)
        tree.nodes.append(decoded_node)

    decode_child(node, tree)

    return tree


def decode_child(node, tree):

    for child in node.children:
        sub_tree = QuadTree(child.center[0], child.center[1], child.size, child.depth)

        pass
    # TODO
    '''
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
    '''
