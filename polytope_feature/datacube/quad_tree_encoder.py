# from . import quad_tree_pb2 as pb2
# from .quad_tree import QuadNode, QuadTree

# # Encoding


# def encode_tree(tree: QuadTree):
#     node = pb2.QuadTree()

#     node.depth = 0

#     for coord in tree.center:
#         node.center.append(coord)

#     for size in tree.size:
#         node.size.append(size)

#     # if len(tree.nodes) != 0:
#     for quad_node in tree.nodes:
#         encoded_node = encode_quad_node(quad_node)
#         node.nodes.append(encoded_node)

#     # if len(tree.children) != 0:
#     for node_child in tree.children:
#         encode_child(node_child, node)

#     # Get bytestring
#     return node.SerializeToString()


# def encode_child(child: QuadTree, pb2_node):
#     child_node = pb2.QuadTree()
#     child_node.depth = child.depth

#     for coord in child.center:
#         child_node.center.append(coord)

#     for size in child.size:
#         child_node.size.append(size)

#     # if len(child.nodes) != 0:
#     for quad_node in child.nodes:
#         encoded_node = encode_quad_node(quad_node)
#         child_node.nodes.append(encoded_node)

#     for c in child.children:
#         encode_child(c, child_node)

#     pb2_node.children.append(child_node)


# def encode_quad_node(quad_node: QuadNode):
#     node = pb2.QuadNode()

#     for i in quad_node.item:
#         node.item.append(i)

#     node.index = quad_node.index
#     return node


# def write_encoded_tree_to_file(tree_bytes, filename):
#     with open(filename, "wb") as fs:
#         fs.write(tree_bytes)


# # Decoding

# def decode_quad_node(pb2_quad_node):
#     node = QuadNode(pb2_quad_node.item, pb2_quad_node.index)
#     return node


# def decode_quad_tree(bytearray):
#     node = pb2.QuadTree()
#     node.ParseFromString(bytearray)

#     tree = QuadTree(node.center[0], node.center[1], node.size, node.depth)

#     for n in node.nodes:
#         decoded_node = decode_quad_node(n)
#         tree.nodes.append(decoded_node)

#     decode_child(node, tree)

#     return tree


# def decode_child(node, tree):

#     for child in node.children:
#         sub_tree = QuadTree(child.center[0], child.center[1], child.size, child.depth)
#         tree.children.append(sub_tree)
#         decode_child(child, sub_tree)
#     if len(node.children) == 0:
#         for quad_node in node.nodes:
#             final_node = QuadNode(quad_node.item, quad_node.index)
#             tree.nodes.append(final_node)


# def read_encoded_tree_from_file(filename):
#     with open(filename, "rb") as fs:


# NOTE : WORKING CODE


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


def write_encoded_qtree_to_file(qtree_bytes, filename):
    with open(filename, "wb") as fs:
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
        qtree.nodes.append(qnode)

    for coded_qchild in coded_qtree.children:
        qchild = decode_qtree_child(coded_qchild)
        qtree.children.append(qchild)

    return qtree


def read_encoded_qtree_from_file(filename):
    with open(filename, "rb") as fs:
        return fs.read()


# NOTE: supposedly optimised code

# from . import quad_tree_pb2 as pb2
# from .quad_tree import QuadNode, QuadTree


# def encode_qtree(qtree: QuadTree) -> bytes:
#     """Encodes a QuadTree into a Protobuf binary string."""
#     coded_qtree = pb2.QuadTree()
#     coded_qtree.size.extend(qtree.size)
#     coded_qtree.center.extend(qtree.center)

#     # Efficiently encode nodes
#     coded_qtree.nodes.extend(encode_quad_node(qnode) for qnode in qtree.nodes)

#     # Efficiently encode children using a stack-based approach to avoid deep recursion
#     stack = [(qtree, coded_qtree.children)]
#     while stack:
#         parent_qtree, coded_children = stack.pop()
#         for child in parent_qtree.children:
#             coded_child = pb2.QuadTree()
#             coded_child.size.extend(child.size)
#             coded_child.center.extend(child.center)
#             coded_child.nodes.extend(encode_quad_node(qnode) for qnode in child.nodes)
#             coded_children.append(coded_child)
#             stack.append((child, coded_child.children))  # Push to process later

#     return coded_qtree.SerializeToString()


# def encode_quad_node(qnode: QuadNode) -> pb2.QuadNode:
#     """Encodes a QuadNode."""
#     return pb2.QuadNode(item=qnode.item, index=qnode.index)


# def write_encoded_qtree_to_file(qtree_bytes: bytes, filename: str):
#     """Writes the encoded QuadTree bytes to a file."""
#     with open(filename, "wb") as fs:
#         fs.write(qtree_bytes)


# def decode_qtree(bytearray: bytes) -> QuadTree:
#     """Decodes a Protobuf binary string into a QuadTree object."""
#     coded_qtree = pb2.QuadTree()
#     coded_qtree.ParseFromString(bytearray)

#     qtree = QuadTree(
#         size=list(coded_qtree.size),
#         x=coded_qtree.center[0],
#         y=coded_qtree.center[1],
#         # nodes=[QuadNode(list(cn.item), cn.index) for cn in coded_qtree.nodes],
#         # children=[]
#     )
#     qtree.nodes = [QuadNode(list(cn.item), cn.index) for cn in coded_qtree.nodes]

#     # Iterative decoding to avoid recursion overhead
#     stack = [(qtree, coded_qtree.children)]
#     while stack:
#         parent_qtree, coded_children = stack.pop()
#         for coded_child in coded_children:
#             child_qtree = QuadTree(
#                 size=list(coded_child.size),
#                 x=coded_child.center[0],
#                 y=coded_child.center[1],
#                 # nodes=[QuadNode(list(cn.item), cn.index) for cn in coded_child.nodes],
#                 # children=[]
#             )
#             child_qtree.nodes = [QuadNode(list(cn.item), cn.index) for cn in coded_child.nodes]
#             parent_qtree.children.append(child_qtree)
#             stack.append((child_qtree, coded_child.children))  # Push children for processing

#     return qtree


# def read_encoded_qtree_from_file(filename: str) -> bytes:
#     """Reads encoded QuadTree bytes from a file."""
#     with open(filename, "rb") as fs:
#         return fs.read()
