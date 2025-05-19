import itertools
from collections import Counter
from typing import List

from ..shapes import ConvexPolytope
from .exceptions import AxisNotFoundError, AxisOverdefinedError, AxisUnderdefinedError


def group(polytopes: List[ConvexPolytope]):
    # Group polytopes into polytopes which share the same axes
    # If the polytopes are orthogonal and not in a union, we first group them together into an additional list
    # so we can treat them together as a single object
    groups = {}
    for p in polytopes:
        if p.is_orthogonal and not p.is_in_union:
            groups.setdefault(tuple(sorted(p.axes())), [[]])[0].append(p)
        else:
            groups.setdefault(tuple(sorted(p.axes())), []).append(p)
    concatenation = []
    for other_group in list(groups.keys()):
        for key in other_group:
            concatenation.append(key)
    return groups, concatenation


def tensor_product(groups):
    # Compute the tensor product of polytope groups
    return list(itertools.product(*groups.values()))


def validate_axes(actual_axes, test_axes):
    # Each axis should be defined only once
    count = Counter(test_axes)
    axes = list(count.keys())
    counts = [count[key] for key in axes]
    for c in zip(axes, counts):
        if c[1] > 1:
            raise AxisOverdefinedError(c[0])

    # Check for missing axes
    for ax in set(actual_axes).difference(set(test_axes)):
        raise AxisUnderdefinedError(ax)

    # Check for too many axes
    for ax in set(test_axes).difference(set(actual_axes)):
        raise AxisNotFoundError(ax)

    return True
