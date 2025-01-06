import os
import re
from pathlib import Path

from .qubed_compressed_tree import CompressedTree


def load_tree():
    path = os.path.dirname(os.path.abspath(__file__))
    data_path = Path(path + "/compressed_tree_extremes.json")
    compressed_tree = CompressedTree.load(data_path)
    tree = compressed_tree.reconstruct_compressed_ecmwf_style()
    return tree


tree = load_tree()


def get_next_axis(tree):
    next_key_val_pairs = list(tree.keys())
    next_axes = []
    for key_val_pair in next_key_val_pairs:
        key, vals = re.split(r'[=]', key_val_pair)
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
    if len(next_key_vals_pairs) == 0:
        return {}
    for key_val_pair in next_key_vals_pairs:
        key, vals = re.split(r"[=]", key_val_pair)
        new_vals = re.split(r'[,]', vals)
        if axis == "latitude":
            return {}
        if axis == key and val in new_vals:
            subtree = tree[key_val_pair]
            return subtree
    # If this subtree doesn't exist, return None
    return None


def select_subtree(tree, path_axis, path_val):
    # TODO: what happens if path_val is compressed and not all compressed values are in the same qubed subtree?
    tree = find_subtree(tree, path_axis, path_val)
    return tree


def subtree(tree, axis, val):
    # TODO: need to do this differently, to be able to handle the compressed vals
    tree_key = axis + "=" + val
    subtree = tree[tree_key]
    return subtree


def get_fdb_coordinates_(tree, coordinates=None):
    if coordinates is None:
        coordinates = {}

    tree_keys = list(tree.keys())
    if len(tree_keys) != 0:
        for key in tree_keys:
            axis, vals = re.split(r"[=]", key)
            new_vals = re.split(r'[,]', vals)

            if axis not in coordinates:
                coordinates[axis] = new_vals
            else:
                coordinates[axis].extend(new_vals)

            subtree = tree[key]
            get_fdb_coordinates_(subtree, coordinates)


def get_fdb_coordinates(tree):
    coordinates = {}
    get_fdb_coordinates_(tree, coordinates)
    for key in coordinates:
        coordinates[key] = list(set(coordinates[key]))
    print(coordinates)
    return coordinates


def get_all_axes(tree, axes=[]):
    tree_keys = list(tree.keys())
    if len(tree_keys) != 0:
        for key in tree_keys:
            axis, vals = re.split(r"[=]", key)
            if axis not in axes:
                axes.append(axis)
            subtree = tree[key]
            get_all_axes(subtree, axes)


def get_axes(tree):
    axes = []
    get_all_axes(tree, axes)
    return axes


new_tree = subtree(subtree(tree, "class", "d1"), "dataset", "extremes-dt")

print(new_tree)
print(list(new_tree.keys()))

print(get_next_ax_vals(new_tree, "expver"))
print(get_axes(new_tree))


# TODO: need to determine ax_vals for the current tree, and also select
