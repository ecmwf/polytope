from copy import deepcopy

from . import index_tree_pb2 as pb2
from .datacube_axis import IntDatacubeAxis
from .index_tree import IndexTree


def encode_tree(tree: IndexTree):
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


def encode_child(tree: IndexTree, child: IndexTree, node, result_size=[]):
    child_node = pb2.Node()

    child_node.axis = child.axis.name

    # Add the result size to the final node
    # TODO: how to assign repeated fields more efficiently?
    # NOTE: this will only really be efficient when we compress and have less leaves
    if len(child.children) == 0:
        result_size.append(len(child.values))
        result_size.append(len(child.indexes))
        child_node.result_size.extend(result_size)
        child_node.indexes.extend(child.indexes)
    # NOTE: do we need this if we parse the tree before it has values?
    # TODO: not clear if child.value is a numpy array or a simple float...
    # TODO: not clear what happens if child.value is a np array since this is not a supported type by protobuf
    if child.result is not None:
        if isinstance(child.result, list):
            child_node.result.extend(child.result)
        else:
            child_node.result.append(child.result)

    # Assign the node value according to the type
    child_node.value.extend(child.values)
    # for child_val in child.values:
    #     child_node.value.append(child_val)
    # if isinstance(child.values[0], int):
    #     for i, child_val in enumerate(child.values):
    #         child_node_val = pb2.Value()
    #         child_node_val.int_val = child_val
    #         child_node.value.append(child_node_val)
    # if isinstance(child.values[0], float):
    #     for i, child_val in enumerate(child.values):
    #         child_node_val = pb2.Value()
    #         child_node_val.double_val = child_val
    #         child_node.value.append(child_node_val)
    # if isinstance(child.values[0], str):
    #     for i, child_val in enumerate(child.values):
    #         child_node_val = pb2.Value()
    #         child_node_val.str_val = child_val
    #         child_node.value.append(child_node_val)
    # if isinstance(child.values[0], pd.Timestamp):
    #     for i, child_val in enumerate(child.values):
    #         child_node_val = pb2.Value()
    #         child_node_val.str_val = child_val.strftime("%Y%m%dT%H%M%S")
    #         child_node.value.append(child_node_val)
    # if isinstance(child.values[0], np.datetime64):
    #     for i, child_val in enumerate(child.values):
    #         child_node_val = pb2.Value()
    #         child_node_val.str_val = pd.to_datetime(str(child_val)).strftime("%Y/%m/%dT%H:%M:%S")
    #         child_node.value.append(child_node_val)
    # if isinstance(child.values[0], np.timedelta64):
    #     for i, child_val in enumerate(child.values):
    #         child_node_val = pb2.Value()
    #         child_node_val.str_val = str(child_val)
    #         child_node.value.append(child_node_val)

    for c in child.children:
        new_result_size = deepcopy(result_size)
        new_result_size.append(len(child.values))
        encode_child(child, c, child_node, new_result_size)

    # NOTE: we append the children once their branch has been completed until the leaf
    node.children.append(child_node)


def decode_tree(datacube, bytearray):
    node = pb2.Node()
    node.ParseFromString(bytearray)

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
        tree.result_size = node.result_size
        tree.indexes = node.indexes
    for child in node.children:
        child_axis = datacube._axes[child.axis]
        child_vals = []
        for child_val in child.value:
            child_vals.append(getattr(child_val, child_val.WhichOneof("value")))
        child_vals = tuple(child_vals)
        child_node = IndexTree(child_axis, child_vals)
        tree.add_child(child_node)
        decode_child(child, child_node, datacube)
