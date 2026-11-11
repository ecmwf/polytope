"""Pruning a sliced ``TensorIndexTree`` into independent sub-trees for chunked extraction.

A caller slices a request once, then repeatedly prunes the tree to a value -- or a set of values -- on each
compressed non-spatial axis (date/time/step/number/param/levelist...) and calls ``datacube.get`` on each pruned
tree.  The pruned trees share no mutable state with the parent, so ``get`` (which reorders and de-duplicates
leaf values and fills ``result``) never touches the parent tree.  Calling ``FDBDatacube.prepare`` on the parent
first puts its points into their final (``get``) order, so every pruned sub-tree's coordinates are known before
any data is fetched.
"""

import numpy as np

from .tensor_index_tree import (
    BulkMergedTensorIndexNode,
    MergedTensorIndexNode,
    TensorIndexTree,
)


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


def _wanted_values(wanted):
    """``wanted`` as a sequence of values: one value selects itself."""
    if isinstance(wanted, (list, tuple, set, frozenset, np.ndarray)):
        return list(wanted)
    return [wanted]


def _select_values(node, wanted):
    """``(values, hits)``: the elements of ``node.values`` matching ``wanted`` and which of ``wanted`` matched.

    ``wanted`` is one value or a sequence of them.  The values are the tree's own objects in the node's order,
    so the compressed-axes expansion of ``FDBDatacube.get`` stays in tree order; ``hits`` are positions in
    ``wanted``, so that a value the tree does not have anywhere can be named.
    """
    choices = _wanted_values(wanted)
    values = []
    hits = set()
    for v in node.values:
        for i, w in enumerate(choices):
            if _value_matches(v, w, node.axis):
                values.append(v)
                hits.add(i)
                break
    return tuple(values), hits


def _copy_node(node, values=None):
    new = TensorIndexTree(node.axis, node.values if values is None else values)
    if isinstance(new.values, np.ndarray):
        new.values = new.values.copy()
    new.indexes = list(node.indexes)
    new.hidden = node.hidden
    new.tags = set(node.tags)
    if node._keep_value_order:
        new._keep_value_order = True
    if node.tag_ids is not None and values is None:
        # per-point tags of an array leaf: shared, not copied per point
        new.tag_sets = node.tag_sets
        new.tag_ids = node.tag_ids
    return new


def _copy_merged(node):
    new = MergedTensorIndexNode(node.axes, node.values)
    new.indexes = list(node.indexes)
    new.hidden = node.hidden
    new.tags = set(node.tags)
    return new


def _copy_subtree(node):
    if isinstance(node, BulkMergedTensorIndexNode):
        # share the node's arrays: a bulk node holds the whole spatial selection
        return node.copy_shared()
    if isinstance(node, MergedTensorIndexNode):
        return _copy_merged(node)
    new = _copy_node(node)
    for child in node.children:
        new.add_child(_copy_subtree(child))
    return new


def _check_select(select, latitude_axis):
    select = dict(select or {})
    for name in select:
        if name in (latitude_axis, "longitude"):
            raise ValueError(f"Cannot select on spatial axis {name!r}")
    return select


def _walk(root, select, latitude_axis):
    """Depth-first copy of the branches matching ``select``; spatial sub-trees are copied whole."""
    matched: dict = {}

    def visit(src, dst):
        kept_any = False
        for child in src.children:
            if isinstance(child, MergedTensorIndexNode) or child.axis.name == latitude_axis:
                dst.add_child(_copy_subtree(child))
                kept_any = True
                continue
            values = None
            name = child.axis.name
            if name in select:
                values, hits = _select_values(child, select[name])
                if not values:
                    continue
                matched.setdefault(name, set()).update(hits)
            new = _copy_node(child, values)
            if len(child.children) == 0:
                # leaf above the latitude level (non-spatial tree): keep it whole
                dst.add_child(new)
                kept_any = True
                continue
            if visit(child, new):
                dst.add_child(new)
                kept_any = True
        return kept_any

    new_root = _copy_node(root)
    visit(root, new_root)
    missing = {}
    for name, wanted in select.items():
        hits = matched.get(name, ())
        absent = [w for i, w in enumerate(_wanted_values(wanted)) if i not in hits]
        if absent:
            missing[name] = absent
    if missing:
        raise ValueError(
            "Values not found in tree: "
            + ", ".join(
                f"{name}={values[0]!r}" if len(values) == 1 else f"{name}={values!r}"
                for name, values in sorted(missing.items())
            )
        )
    return new_root


def prune(tree, select=None, latitude_axis="latitude") -> TensorIndexTree:
    if not tree.is_root():
        raise ValueError("prune() must be called on the root of a tree")
    pruned = _walk(tree, _check_select(select, latitude_axis), latitude_axis)
    assert pruned is not None
    return pruned
