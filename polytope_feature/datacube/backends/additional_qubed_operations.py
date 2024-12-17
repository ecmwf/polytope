import re
import json
from pathlib import Path

from qubed_compressed_trees import CompressedTree

import os


def load_tree():
    path = os.path.dirname(os.path.abspath(__file__))
    data_path = Path(path + "/compressed_tree_extremes.json")
    compressed_tree = CompressedTree.load(data_path)
    tree = compressed_tree.reconstruct_compressed_ecmwf_style()
    return tree


def get_next_axis(tree):
    # TODO: need to find the next axis
    next_key_val_pairs = list(tree.keys())
    next_axes = []
    for key_val_pair in next_key_val_pairs:
        key, vals = re.split(r'[=]', key_val_pair)
        vals = re.split(r'[,]', vals)
        if key not in next_axes:
            next_axes.append(key)
    return next_axes


def get_next_ax_vals(tree, ax_name):
    next_key_val_pairs = list(tree.keys())
    next_vals = []
    for key_val_pair in next_key_val_pairs:
        key, vals = re.split(r"[=]", key_val_pair)
        if key == ax_name:
            vals = re.split(r'[,]', vals)
            next_vals.extend(vals)
    return next_vals


def find_subtree(tree, axis, val):
    next_key_vals_pairs = list(tree.keys())
    for key_val_pair in next_key_vals_pairs:
        key, vals = re.split(r"[=]", key_val_pair)
        new_vals = re.split(r'[,]', vals)
        if axis == "latitude":
            return None
        if axis == key and val in new_vals:
            subtree = tree[key_val_pair]
            return subtree
    # If this subtree doesn't exist, return None
    return None


def subtree(tree, axis, val):
    # TODO: need to do this differently, to be able to handle the compressed vals

    # TODO: need to first decompose next subtree keys and look if the value is in them
    tree_key = axis + "=" + val
    subtree = tree[tree_key]
    return subtree


new_tree = subtree(subtree(tree, "class", "d1"), "dataset", "extremes-dt")

print(list(new_tree.keys()))

print(get_next_ax_vals(new_tree, "expver"))


# TODO: need to determine ax_vals for the current tree, and also select
