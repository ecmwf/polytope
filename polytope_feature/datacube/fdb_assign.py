"""Scatter the values of one gribjump field into the leaves of a request tree.

A gribjump ``extract`` call is a list of (MARS path, index ranges) requests and its result iterator yields one
``ExtractionResult`` per request, i.e. one per field.  ``FDBDatacube`` builds one request per *field* of one
*spatial sub-tree*: the tree's compressed non-spatial axes (``param``, ``step``, ``number``, ...) are expanded into
the cartesian product of their values, and every field of a sub-tree asks for the same index ranges.

Each field's values are taken from ``result.values_flat`` -- one contiguous float64 view over all ranges of the
field, in request order -- rather than from the per-range ``result.values`` list, which costs a numpy object plus a
list slot per range.  On HEALPix nested grids a bounding box shatters into roughly one range per 1.6 points, so the
per-range representation cost hundreds of bytes per value where the flat one costs eight.

:class:`FieldRequests` holds the per-sub-tree bookkeeping shared by all its fields and caches the
:class:`ScatterPlan` built from it.  The plan is three arrays and one list of leaves, so one plan plus one field's
values is alive at a time whatever the number of ranges or fields:

* ``leaves``: the leaf nodes the sub-tree's values belong to, in tree order,
* ``leaf_offsets``: where each leaf's points start in the field's destination order,
* ``order``: for each destination position, the position of its value in ``values_flat`` (``None`` when the two
  orders agree, which they do on row-ordered grids).
"""

import numpy as np

from .tree_values import finalise_result

__all__ = ["FieldRequests", "ScatterPlan", "field_values_flat"]


def _result_owner(node):
    """The node a request range's results belong to (merged lat/lon leaves are fetched through a proxy)."""
    return getattr(node, "_result_owner", node)


def field_values_flat(result):
    """One field's values as a contiguous float64 array, or ``None`` when gribjump had no data for the field.

    Prefers pygribjump's ``values_flat`` (a view over the whole result, so no per-range objects are created) and
    falls back to concatenating ``values`` for result objects that do not have it.  Bitmap-missing points are NaN
    in the buffer gribjump fills, exactly as they are in the per-range ``values`` views, which are slices of the
    same buffer; ``masks_flat`` is therefore not needed to reproduce them.
    """
    flat = getattr(result, "values_flat", None)
    if flat is None:
        chunks = result.values
        if len(chunks) == 0:
            return None
        flat = np.concatenate([np.asarray(c, dtype=np.float64) for c in chunks])
    if flat.size == 0:
        # a MARS path with no GRIB message behind it: gribjump returns an empty result for the whole field
        return None
    return np.asarray(flat, dtype=np.float64)


class FieldRequests:
    """The leaves and index ranges of one spatial sub-tree, shared by every field requested for it.

    ``original_indices[i]`` is the position, in tree order, of the ``i``-th request range after sorting the ranges
    by grid index; ``node_ranges[p]`` is the one-element list of nodes of the range at tree-order position ``p``
    and ``ranges[i]`` is the ``i``-th sorted range.  ``n_fields`` is how many fields of this sub-tree the call
    asks for (the size of the product of the compressed axes' values).
    """

    __slots__ = ("original_indices", "node_ranges", "ranges", "n_fields", "value_orders", "_plan")

    def __init__(self, original_indices, node_ranges, ranges, n_fields, value_orders):
        self.original_indices = original_indices
        self.node_ranges = node_ranges
        self.ranges = ranges
        self.n_fields = n_fields
        self.value_orders = value_orders
        self._plan = None

    def plan(self, allocate=False):
        """The sub-tree's :class:`ScatterPlan`, built on first use.  With ``allocate``, also pre-allocate the
        leaves' result arrays (``n_points x n_fields`` float64, NaN-filled)."""
        if self._plan is None:
            self._plan = ScatterPlan(self)
            if allocate:
                self._plan.allocate_results()
        return self._plan

    def release(self):
        """Drop the plan: nothing of this sub-tree stays alive once its last field has been consumed."""
        self._plan = None

    def finish_and_release(self):
        if self._plan is not None:
            self._plan.finish()
        self.release()


class ScatterPlan:
    """Where each value of one field of a spatial sub-tree goes: see the module docstring."""

    __slots__ = (
        "leaves",
        "leaf_offsets",
        "leaf_sources",
        "order",
        "n_fields",
        "n_values",
        "_prior",
        "_missing_fields",
    )

    def __init__(self, requests: FieldRequests):
        node_ranges = requests.node_ranges
        original_indices = requests.original_indices
        n_ranges = len(original_indices)

        # Leaves in tree order: node_ranges is built while descending the tree, one entry per range.
        leaves = []
        leaf_of_position = {}
        for position in range(n_ranges):
            owner = _result_owner(node_ranges[position][0])
            index = leaf_of_position.get(id(owner))
            if index is None:
                index = leaf_of_position[id(owner)] = len(leaves)
                leaves.append(owner)

        # Per request range, in the order gribjump returns them (sorted by grid index): which leaf, how many
        # values, and where they start in values_flat.
        leaf_of_range = np.fromiter(
            (leaf_of_position[id(_result_owner(node_ranges[p][0]))] for p in original_indices),
            dtype=np.int64,
            count=n_ranges,
        )
        lengths = np.fromiter((hi - lo for lo, hi in requests.ranges), dtype=np.int64, count=n_ranges)
        source = np.cumsum(lengths) - lengths
        n_values = lengths.sum().item()

        # A leaf's ranges are returned in ascending grid index order, which is the order of its values, so
        # grouping the ranges by leaf (stably) lays the destination out leaf by leaf, each leaf's points in order.
        by_leaf = np.argsort(leaf_of_range, kind="stable")
        grouped = lengths[by_leaf]
        destination = np.cumsum(grouped) - grouped
        order = np.repeat((source[by_leaf] - destination).astype(np.int32), grouped)
        order += np.arange(n_values, dtype=np.int32)

        points_per_leaf = np.bincount(leaf_of_range, weights=lengths, minlength=len(leaves)).astype(np.int64)
        leaf_offsets = np.zeros(len(leaves) + 1, dtype=np.int64)
        np.cumsum(points_per_leaf, out=leaf_offsets[1:])

        for index, leaf in enumerate(leaves):
            value_order = requests.value_orders.get(id(leaf))
            if value_order is not None:
                # merged polygon row: its values stayed ascending, so put the results back into that order
                block = order[leaf_offsets[index] : leaf_offsets[index + 1]]  # noqa: E203
                block[np.asarray(value_order, dtype=np.intp)] = block.copy()

        self.leaves = leaves
        self.leaf_offsets = leaf_offsets
        self.n_fields = requests.n_fields
        self.n_values = n_values
        self.leaf_sources = order[leaf_offsets[:-1]] if n_values else order[:0]
        # Where every leaf's values are one ascending run of values_flat (any grid whose points are stored row by
        # row), each leaf is one slice of the buffer and the positions need not be kept at all.
        self.order = None if _runs_per_leaf(order, leaf_offsets) else order
        self._prior = None
        self._missing_fields = set()

    def n_points(self, index):
        return (self.leaf_offsets[index + 1] - self.leaf_offsets[index]).item()

    def allocate_results(self):
        """Give every leaf its result array for the whole call: ``n_points x n_fields`` float64, NaN-filled."""
        self._prior = []
        for index, leaf in enumerate(self.leaves):
            self._prior.append(leaf.result)
            leaf.result = np.full(self.n_points(index) * self.n_fields, np.nan, dtype=np.float64)

    def _check(self, flat):
        if flat.size != self.n_values:
            raise ValueError(f"gribjump returned {flat.size} values for a field of {self.n_values} points")

    def assign_field(self, flat, field_index):
        """Write one field's values into the pre-allocated result of every leaf of the sub-tree.

        ``flat`` is the field's ``values_flat`` or ``None`` for a field gribjump has no message for, whose values
        stay NaN until :meth:`finish` turns them into ``None``.
        """
        if flat is None:
            self._missing_fields.add(field_index)
            return
        self._check(flat)
        offsets = self.leaf_offsets
        order = self.order
        for index, leaf in enumerate(self.leaves):
            start, end = offsets[index], offsets[index + 1]
            n = end - start
            destination = leaf.result[field_index * n : (field_index + 1) * n]  # noqa: E203
            if order is None:
                source = self.leaf_sources[index]
                destination[:] = flat[source : source + n]  # noqa: E203
            else:
                np.take(flat, order[start:end], out=destination)

    def field_arrays(self, flat):
        """One field's values as a fresh float64 array per leaf, in tree order: ``[(leaf, values), ...]``.

        The arrays are copies, so they stay valid once the gribjump result they came from has been released.
        """
        self._check(flat)
        offsets = self.leaf_offsets
        order = self.order
        out = []
        for index, leaf in enumerate(self.leaves):
            start, end = offsets[index], offsets[index + 1]
            if order is None:
                source = self.leaf_sources[index]
                out.append((leaf, np.array(flat[source : source + end - start], dtype=np.float64)))  # noqa: E203
            else:
                out.append((leaf, np.take(flat, order[start:end])))
        return out

    def finish(self):
        """Close the sub-tree: turn missing fields into ``None`` and append to any result the leaves already had."""
        if self._prior is None:
            return
        for index, leaf in enumerate(self.leaves):
            result = leaf.result
            if self._missing_fields:
                result = _with_missing_fields(result, self.n_points(index), self.n_fields, self._missing_fields)
            prior = self._prior[index]
            if prior is not None and len(prior) != 0:
                result = finalise_result([list(prior), list(result)])
            leaf.result = result
        self._prior = None


def _with_missing_fields(values, n_points, n_fields, missing_fields):
    """A leaf's result as an object array holding ``None`` for every point of a field gribjump did not have."""
    out = np.empty(n_points * n_fields, dtype=object)
    for field_index in range(n_fields):
        block = slice(field_index * n_points, (field_index + 1) * n_points)
        if field_index in missing_fields:
            out[block] = None
        else:
            # keep numpy scalars, as the per-range results did
            out[block] = list(values[block])
    return out


def _runs_per_leaf(order, leaf_offsets):
    """True when every leaf's values are consecutive and ascending in ``values_flat``."""
    if order.size < 2:
        return True
    steps = np.diff(order) == 1
    steps[leaf_offsets[1:-1] - 1] = True  # a leaf boundary may jump anywhere
    return bool(np.all(steps))
