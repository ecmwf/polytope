"""Pruning a sliced ``TensorIndexTree`` into independent sub-trees for chunked extraction.

A caller slices a request once, then repeatedly prunes the tree to one value on each compressed non-spatial axis
(date/time/step/number/param/levelist...) and a contiguous band of latitude nodes, and calls ``datacube.get`` on
each pruned tree.  The pruned trees share no mutable state with the parent, so ``get`` (which reorders and
de-duplicates leaf values and fills ``result``) never touches the parent tree.  Calling ``FDBDatacube.prepare`` on
the parent first puts its points into their final (``get``) order, so every pruned band's coordinates are known
before any data is fetched.
"""

import math

import numpy as np

from .tensor_index_tree import MergedTensorIndexNode, TensorIndexTree


def _value_matches(node_value, wanted, axis):
    try:
        if node_value == wanted:
            return True
    except (TypeError, ValueError):
        return False
    if getattr(axis, "can_round", False) and isinstance(node_value, (int, float, np.number)):
        try:
            return abs(node_value - wanted) <= 2 * axis.tol
        except TypeError:
            return False
    return False


def _select_value(node, wanted):
    """Return the element of ``node.values`` equal to ``wanted`` (the tree's own object), or None."""
    for v in node.values:
        if _value_matches(v, wanted, node.axis):
            return v
    return None


def _copy_node(node, values=None):
    new = TensorIndexTree(node.axis, node.values if values is None else values)
    if isinstance(new.values, np.ndarray):
        new.values = new.values.copy()
    new.indexes = list(node.indexes)
    new.hidden = node.hidden
    new.tags = set(node.tags)
    return new


def _copy_merged(node):
    new = MergedTensorIndexNode(node.axes, node.values)
    new.indexes = list(node.indexes)
    new.hidden = node.hidden
    new.tags = set(node.tags)
    return new


def _copy_subtree(node):
    if isinstance(node, MergedTensorIndexNode):
        return _copy_merged(node)
    new = _copy_node(node)
    for child in node.children:
        new.add_child(_copy_subtree(child))
    return new


def _subtree_points(node):
    if isinstance(node, MergedTensorIndexNode):
        return 1
    if len(node.children) == 0:
        return len(node.values)
    return sum(_subtree_points(c) for c in node.children)


def _check_select(select, latitude_axis):
    select = dict(select or {})
    for name in select:
        if name in (latitude_axis, "longitude"):
            raise ValueError(f"Cannot select on spatial axis {name!r}; use latitude_range instead")
    return select


def _walk(root, select, latitude_axis, on_spatial, build):
    """Depth-first traversal of the branches matching ``select``.

    ``on_spatial(node)`` is called for each latitude node / merged leaf in traversal order and returns a copy to
    attach (or None).  When ``build`` is true a pruned copy of the tree is returned.
    """
    matched = set()

    def visit(src, dst):
        kept_any = False
        for child in src.children:
            if isinstance(child, MergedTensorIndexNode) or child.axis.name == latitude_axis:
                copy = on_spatial(child)
                if copy is not None:
                    dst.add_child(copy)
                    kept_any = True
                continue
            values = None
            name = child.axis.name
            if name in select:
                v = _select_value(child, select[name])
                if v is None:
                    continue
                matched.add(name)
                values = (v,)
            new = _copy_node(child, values) if build else None
            if len(child.children) == 0:
                # leaf above the latitude level (non-spatial tree): keep it whole
                if build:
                    dst.add_child(new)
                kept_any = True
                continue
            if visit(child, new):
                if build:
                    dst.add_child(new)
                kept_any = True
        return kept_any

    new_root = _copy_node(root) if build else None
    visit(root, new_root)
    missing = set(select) - matched
    if missing:
        raise ValueError(
            "Values not found in tree: " + ", ".join(f"{name}={select[name]!r}" for name in sorted(missing))
        )
    return new_root


def latitude_point_counts(tree, select=None, latitude_axis="latitude"):
    select = _check_select(select, latitude_axis)
    counts = []

    def on_spatial(node):
        counts.append(_subtree_points(node))
        return None

    _walk(tree, select, latitude_axis, on_spatial, build=False)
    return counts


def prune(tree, select=None, latitude_range=None, latitude_axis="latitude") -> TensorIndexTree:
    if not tree.is_root():
        raise ValueError("prune() must be called on the root of a tree")
    select = _check_select(select, latitude_axis)
    if latitude_range is None:
        lo, hi = 0, math.inf
    else:
        lo, hi = latitude_range
        if lo < 0 or hi < lo:
            raise ValueError(f"Invalid latitude_range {latitude_range!r}")
    counter = [0]

    def on_spatial(node):
        k = counter[0]
        counter[0] += 1
        if lo <= k < hi:
            return _copy_subtree(node)
        return None

    pruned = _walk(tree, select, latitude_axis, on_spatial, build=True)
    assert pruned is not None
    return pruned
