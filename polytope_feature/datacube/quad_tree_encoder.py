import math
from copy import deepcopy

from . import quad_tree_pb2 as pb2
from .quad_tree import QuadTree, QuadNode


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
