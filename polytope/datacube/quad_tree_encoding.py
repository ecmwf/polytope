from . import quad_tree_pb2 as pb2
from .quad_tree import QuadNode, QuadTree


def encode_qtree(qtree: QuadTree):
    coded_qtree = pb2.QuadTree()
    coded_qtree.size.extend(qtree.size)
    coded_qtree.center.extend(qtree.center)
    for qnode in qtree.nodes:
        coded_qnode = encode_quad_node(qnode)
        coded_qtree.nodes.append(coded_qnode)
    for qchild in qtree.children:
        coded_child = encode_quad_tree_child(qchild)
        coded_qtree.children.append(coded_child)

    # Write to file
    return coded_qtree.SerializeToString()


def encode_quad_tree_child(qtree: QuadTree):
    coded_qtree = pb2.QuadTree()
    coded_qtree.size.extend(qtree.size)
    coded_qtree.center.extend(qtree.center)
    for qnode in qtree.nodes:
        coded_qnode = encode_quad_node(qnode)
        coded_qtree.nodes.append(coded_qnode)
    for qchild in qtree.children:
        coded_child = encode_quad_tree_child(qchild)
        coded_qtree.children.append(coded_child)
    return coded_qtree


def encode_quad_node(qnode: QuadNode):
    coded_qnode = pb2.QuadNode()
    coded_qnode.item.extend(qnode.item)
    coded_qnode.index = qnode.index
    return coded_qnode


def write_encoded_qtree_to_file(qtree_bytes):
    with open("encodedQTree", "wb") as fs:
        fs.write(qtree_bytes)


def decode_qtree(bytearray):
    coded_qtree = pb2.QuadTree()
    coded_qtree.ParseFromString(bytearray)

    qtree = QuadTree()

    qtree.size = tuple(coded_qtree.size)
    qtree.center = tuple(coded_qtree.center)

    for coded_qnode in coded_qtree.nodes:
        qnode_item = tuple(coded_qnode.item)
        qnode_index = coded_qnode.index
        qnode = QuadNode(qnode_item, qnode_index)
        # qnode.item = coded_qnode.item
        # qnode.index = coded_qnode.index
        qtree.nodes.append(qnode)

    for coded_qchild in coded_qtree.children:
        qchild = decode_qtree_child(coded_qchild)
        qtree.children.append(qchild)

    return qtree


def decode_qtree_child(coded_qtree):
    qtree = QuadTree()

    qtree.size = tuple(coded_qtree.size)
    qtree.center = tuple(coded_qtree.center)

    for coded_qnode in coded_qtree.nodes:
        qnode_item = tuple(coded_qnode.item)
        qnode_index = coded_qnode.index
        qnode = QuadNode(qnode_item, qnode_index)
        # qnode = QuadNode()
        # qnode.item = coded_qnode.item
        # qnode.index = coded_qnode.index
        qtree.nodes.append(qnode)

    for coded_qchild in coded_qtree.children:
        qchild = decode_qtree_child(coded_qchild)
        qtree.children.append(qchild)

    return qtree


def read_encoded_qtree_from_file():
    with open("encodedQTree", "rb") as fs:
        return fs.read()
