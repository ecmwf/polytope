"""Fold the latitude -> longitude layers of a prepared request tree into one array-backed node.

``FDBDatacube.prepare``/``get`` reach the spatial layers of a structured (hullslicer) tree as one
latitude node per grid row, each holding one longitude leaf per piece of the request shape.
:func:`fold_spatial_rows` replaces those layers by a single
:class:`~polytope_feature.datacube.tensor_index_tree.BulkGridTensorIndexNode` holding the whole
field's coordinates and canonical grid indexes as arrays, so that the request ranges come from one
sort of the field's indexes instead of one sort per row (on HEALPix nested grids that is hundreds of
ranges instead of hundreds of thousands) and the per-point Python of the legacy request planning
disappears.

The point order is the order of the sliced rows, which is the order the legacy CovJSON encoders
read the tree in: the latitude rows in tree order and, within a row, the longitude
leaves in tree order, each leaf's points in grid-index order (or, for the merged polygon rows of
``tree_rows.RowMerger``, in ascending longitude order, which is the order their results come back
in).

Nothing is held per point.  The shape of the fold is counted first, so the coordinates and the
indexes are written straight into their final arrays one leaf at a time: apart from the destination
there is never more than one row's worth of values alive, and the only per-point Python object is the
list of ints a mapper's ``unmap`` returns for one leaf.
"""

import numpy as np

from .tensor_index_tree import BulkGridTensorIndexNode

__all__ = ["fold_spatial_rows"]


def _leaf_indexes(datacube, lon_child, leaf_path):
    """The grid indexes of one longitude leaf, in the order its values are stored."""
    key_value_path = {lon_child.axis.name: lon_child.values}
    leaf_path["index"] = lon_child.indexes
    key_value_path, leaf_path, datacube.unwanted_path = lon_child.axis.unmap_path_key(
        key_value_path, leaf_path, datacube.unwanted_path
    )
    return np.asarray(key_value_path["values"], dtype=np.int64)


def _unmap_latitude(datacube, lat_child, leaf_path):
    key_value_path = {lat_child.axis.name: lat_child.values}
    key_value_path, leaf_path, datacube.unwanted_path = lat_child.axis.unmap_path_key(
        key_value_path, leaf_path, datacube.unwanted_path
    )
    leaf_path.update(key_value_path)


class _TagTable:
    """The distinct tag sets of a fold, and which of them each span of points carries.

    ``tag_ids`` is only materialised when the fold's points do not all carry the same tags, which is
    the usual case (one shape, or several shapes sharing a tag).
    """

    def __init__(self, n_points):
        self.n_points = n_points
        self.tag_sets = []
        self._ids_of = {}
        self._spans = []

    def _id(self, tags):
        tag_id = self._ids_of.get(tags)
        if tag_id is None:
            tag_id = self._ids_of[tags] = len(self.tag_sets)
            self.tag_sets.append(tags)
        return tag_id

    def add(self, start, stop, lat_tags, lon_child):
        """Record the tags of the points ``start:stop``, which come from one longitude leaf."""
        if lon_child.tag_ids is None:
            self._spans.append((start, stop, self._id(frozenset(lat_tags | lon_child.tags))))
            return
        ids = np.asarray([self._id(frozenset(lat_tags | tags)) for tags in lon_child.tag_sets], dtype=np.int32)
        self._spans.append((start, stop, ids[lon_child.tag_ids]))

    def ids(self):
        if len(self.tag_sets) < 2:
            return None
        tag_ids = np.empty(self.n_points, dtype=np.int32)
        for start, stop, value in self._spans:
            tag_ids[start:stop] = value
        return tag_ids


def _fold_rows(datacube, requests, leaf_path, rows, n_points):
    """Fill the fold's arrays row by row; returns ``(coordinates, indexes, tag_sets, tag_ids)``."""
    coordinates = np.empty((n_points, 2), dtype=np.float64)
    indexes = np.empty(n_points, dtype=np.int64)
    tags = _TagTable(n_points)
    at = 0
    for lat_child, row_length in rows:
        _unmap_latitude(datacube, lat_child, leaf_path)
        coordinates[at : at + row_length, 0] = lat_child.values[0]  # noqa: E203
        for lon_child in lat_child.children:
            leaf_indexes = _leaf_indexes(datacube, lon_child, leaf_path)
            n = leaf_indexes.size
            if n == 0:
                continue
            values = np.asarray(lon_child.values, dtype=np.float64)
            if not lon_child._keep_value_order and n > 1:
                # a box leaf's points come back in grid-index order, as ``prepare`` leaves its values
                order = np.argsort(leaf_indexes, kind="stable")
                if not np.array_equal(order, np.arange(n)):
                    leaf_indexes = leaf_indexes[order]
                    values = values[order]
            coordinates[at : at + n, 1] = values  # noqa: E203
            indexes[at : at + n] = leaf_indexes  # noqa: E203
            tags.add(at, at + n, lat_child.tags, lon_child)
            at += n
    assert at == n_points
    return coordinates, indexes, tags.tag_sets, tags.ids()


def _drop_duplicate_indexes(coordinates, indexes, tag_ids, row_lengths):
    """Keep the first occurrence of every grid index, as the per-row request planning does.

    A point can be reached from two rows when a box overlaps itself across the longitude seam.
    Returns the compacted arrays, or the originals when every index is unique.
    """
    if indexes.size < 2:
        return coordinates, indexes, tag_ids, row_lengths
    _, keep = np.unique(indexes, return_index=True)
    if keep.size == indexes.size:
        return coordinates, indexes, tag_ids, row_lengths
    keep.sort()
    row_of_point = np.searchsorted(np.cumsum(row_lengths), keep, side="right")
    row_lengths = np.bincount(row_of_point, minlength=row_lengths.size)
    return (
        coordinates[keep],
        indexes[keep],
        None if tag_ids is None else tag_ids[keep],
        row_lengths,
    )


def fold_spatial_rows(datacube, requests, leaf_path):
    """Replace the latitude -> longitude children of ``requests`` by one ``BulkGridTensorIndexNode``.

    ``requests`` is the node above the latitude layer and ``leaf_path`` the gribjump path built for
    it so far; the fold unmaps the spatial axes into ``leaf_path`` exactly as the per-row planning
    does, so the caller can derive the field's path from it.  Returns the new node, or ``None``
    when the nearest-point search left no point at all (the branch is then removed).
    """
    datacube.nearest_lat_lon_search(requests)
    if len(requests.children) == 0:
        return None

    lat_ax = requests.children[0].axis
    lon_ax = requests.children[0].children[0].axis

    # the shape of the fold, so that the points can be written straight into their final arrays
    rows = []
    lat_values = []
    row_lengths = []
    n_points = 0
    for lat_child in requests.children:
        row_length = sum(len(lon_child.values) for lon_child in lat_child.children)
        if row_length == 0:
            continue
        rows.append((lat_child, row_length))
        lat_values.append(lat_child.values[0])
        row_lengths.append(row_length)
        n_points += row_length

    if n_points == 0:
        for lat_child in list(requests.children):
            requests.children.remove(lat_child)
            lat_child._parent = None
        requests.remove_branch()
        return None

    coordinates, indexes, tag_sets, tag_ids = _fold_rows(datacube, requests, leaf_path, rows, n_points)
    del rows
    for lat_child in list(requests.children):
        requests.children.remove(lat_child)
        lat_child._parent = None

    lat_values = np.asarray(lat_values, dtype=np.float64)
    row_lengths = np.asarray(row_lengths, dtype=np.int64)
    coordinates, indexes, tag_ids, row_lengths = _drop_duplicate_indexes(coordinates, indexes, tag_ids, row_lengths)
    kept_rows = row_lengths > 0
    if not np.all(kept_rows):
        lat_values = lat_values[kept_rows]
        row_lengths = row_lengths[kept_rows]

    grid_node = BulkGridTensorIndexNode(
        [lat_ax, lon_ax],
        lat_values,
        None,
        indexes,
        tag_ids=tag_ids,
        tag_sets=tag_sets,
        row_lengths=row_lengths,
        coordinates=coordinates,
    )
    requests.add_child(grid_node)
    return grid_node
