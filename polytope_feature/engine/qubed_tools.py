import functools
from typing import Iterable

from qubed import Qube, set_operations


def compress_w_leaf_attrs(q: Qube, attr_str) -> Qube:

    def find_unique_leaf_attrs(attr_str, a: Qube, b: Qube):
        seen = set()
        input_attrs = []

        for leaf in list(a.compressed_leaf_nodes()) + list(b.compressed_leaf_nodes()):
            attrs = getattr(leaf[0], attr_str, None)
            if attrs:
                for attr in attrs:
                    if attr is not None and id(attr) not in seen:
                        input_attrs.append(attr)
                        seen.add(id(attr))
        return input_attrs

    def assign_attrs_to_union(attr_str, a: Qube, b: Qube, out: Qube):
        input_leaves = [leaf[0] for leaf in a.compressed_leaf_nodes()] + [leaf[0] for leaf in b.compressed_leaf_nodes()]
        output_leaves = [leaf[0] for leaf in out.compressed_leaf_nodes()]

        input_attrs = find_unique_leaf_attrs(attr_str, a, b)

        if len(output_leaves) < len(input_leaves):
            merged = []
            for p in input_attrs:
                if p is None:
                    continue
                if isinstance(p, list):
                    merged.extend(p)
                else:
                    merged.append(p)

            if merged:
                for leaf in output_leaves:
                    setattr(leaf, attr_str, merged)
        else:
            transfer_attr(attr_str, input_leaves, output_leaves)

    def union(a: Qube, b: Qube) -> Qube:
        b = type(q).make_root(children=(b,), update_depth=False)
        out = set_operations.set_operation(a, b, set_operations.SetOperation.UNION, type(q))

        assign_attrs_to_union(attr_str, a, b, out)
        return out

    new_children = [compress_w_leaf_attrs(c, attr_str) for c in q.children]
    if len(new_children) > 1:
        new_children = list(functools.reduce(union, new_children, Qube.empty()).children)

    def transfer_attr(attr_str, old_children, new_children):
        for old, new in zip(old_children, new_children):
            if hasattr(old, attr_str):
                old_attr = getattr(old, attr_str)
                setattr(new, attr_str, old_attr)

    transfer_attr(attr_str, q.children, new_children)

    return q.replace(children=tuple(sorted(new_children)))


def compressed_leaf_nodes(qube) -> "Iterable[tuple[dict[str, str], Qube]]":
    if not qube.children:
        yield qube
    for child in qube.children:
        for leaf in compressed_leaf_nodes(child):
            yield leaf
