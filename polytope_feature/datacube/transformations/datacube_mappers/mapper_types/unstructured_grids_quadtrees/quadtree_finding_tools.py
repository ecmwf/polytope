from .....quad_tree_encoder import encode_qtree, decode_qtree, write_encoded_qtree_to_file, read_encoded_qtree_from_file
from .....quad_tree import QuadTree

import os
import sys

import time

import pickle

import sys

# NOTE : CODE USING PICKLE STORAGE OF QUADTREE


# def find_quadtree(grid_hash, point_cloud):
#     # print(sys.path)
#     script_dir = os.path.dirname(os.path.abspath(__file__))

#     # quad_tree_file = quadtree_mapping.get(grid_hash, None)
#     all_files = os.listdir(script_dir)

#     grid_file_path = script_dir + "/" + grid_hash + ".bin"

#     quad_tree_file = grid_hash

#     if (grid_hash + ".bin") not in all_files:
#         quad_tree_file = None

#     if quad_tree_file is None:

#         # Need to generate quadtree and store it in a file
#         # then need to store the file_name with the grid hash in the quadtree_mapping dict
#         # and then assign the quad_tree_file path to pass in the rest of the method
#         tree = QuadTree()
#         tree.build_point_tree(point_cloud)

#         # Store the tree in a pickle
#         with open(grid_file_path, "wb") as f:
#             pickle.dump(tree, f)
#         return tree

#     quad_tree = retrieve_quad_tree(grid_file_path)
#     return quad_tree


# def retrieve_quad_tree(quad_tree_file):
#     print("DETECTED QUADTREE ALREADY PRODUCED")
#     # encoded_tree = read_encoded_qtree_from_file(quad_tree_file)
#     # tree = decode_qtree(encoded_tree)
#     with open(quad_tree_file, "rb") as f:
#         tree = pickle.load(f)
#     return tree


#  NOTE: CODE USING PROTOBUF ENCODINGS OF QUADTREE


def find_quadtree(grid_hash, point_cloud):
    # print(sys.path)
    script_dir = os.path.dirname(os.path.abspath(__file__))

    # quad_tree_file = quadtree_mapping.get(grid_hash, None)
    all_files = os.listdir(script_dir)

    grid_file_path = script_dir + "/" + grid_hash

    quad_tree_file = grid_hash
    if grid_hash not in all_files:
        quad_tree_file = None

    if quad_tree_file is None:

        # Need to generate quadtree and store it in a file
        # then need to store the file_name with the grid hash in the quadtree_mapping dict
        # and then assign the quad_tree_file path to pass in the rest of the method
        tree = QuadTree()
        tree.build_point_tree(point_cloud)

        print("SIZE OF QUADTREE")
        from pympler import asizeof
        print(asizeof.asizeof(tree))

        time1 = time.time()
        encoded_tree = encode_qtree(tree)
        print("LOOK NOW")
        print(time.time() - time1)
        write_encoded_qtree_to_file(encoded_tree, grid_file_path)

        quad_tree_file = grid_hash
        # quadtree_mapping[grid_hash] = grid_file_path
        return tree

    quad_tree = retrieve_quad_tree(grid_file_path)
    return quad_tree


def retrieve_quad_tree(quad_tree_file):
    print("DETECTED QUADTREE ALREADY PRODUCED")
    encoded_tree = read_encoded_qtree_from_file(quad_tree_file)
    time1 = time.time()
    tree = decode_qtree(encoded_tree)
    print("TIME TO DECODE PROTOBUF")
    print(time.time() - time1)
    return tree


# This would need to be long-lived so maybe a yaml is better?
# TODO: don't need this??
quadtree_mapping = {}
