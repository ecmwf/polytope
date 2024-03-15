import index_tree_pb2 as pb2

from .index_tree import IndexTree


def encode_tree(tree: IndexTree):
    node = pb2.Node()

    node.axis = tree.axis.name
    if tree.result is not None:
        node.result = tree.result

    # Assign the node value according to the type
    if isinstance(tree.value, int):
        node.int_val = tree.value
    if isinstance(tree.value, float):
        node.double_val = tree.value
    if isinstance(tree.value, str):
        node.str_val = tree.value

    # Nest children in protobuf root tree node
    for c in tree.children:
        encode_child(tree, c)

    # Write to file
    with open("./serializedTree", "wb") as fd:
        fd.write(node.SerializeToString())


# TODO: complete the type mappings to the right value protobuf attribute and use as a factory?
# type_mappings = {int: "int_val",
#                  str: "str_val",
#                  float: "double_val"}

def encode_child(tree: IndexTree, child: IndexTree):
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

    for c in child.children:
        encode_child(child, c)

    # NOTE: we append the children once their branch has been completed until the leaf
    tree.children.append(child)


def decode_tree(tree: IndexTree, filename):
    pass
