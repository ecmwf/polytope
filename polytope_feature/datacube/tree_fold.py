"""Fold the latitude -> longitude layers of a prepared request tree into one array-backed node.

``FDBDatacube.prepare``/``get`` reach the spatial layers of a structured (hullslicer) tree as one
latitude node per grid row, each holding one longitude leaf per piece of the request shape.  With
``bulk_grid_leaves`` set, :func:`fold_into_bulk_grid` replaces those layers by a single
:class:`~polytope_feature.datacube.tensor_index_tree.BulkGridTensorIndexNode` holding the whole
field's coordinates and canonical grid indexes as arrays, so that the request ranges come from one
sort of the field's indexes instead of one sort per row (on HEALPix nested grids that is hundreds of
ranges instead of hundreds of thousands) and the per-point Python of the legacy request planning
disappears.

The point order is the one ``prepare`` produces without the fold, which is the order the legacy
CovJSON encoders read the tree in: the latitude rows in tree order and, within a row, the longitude
leaves in tree order, each leaf's points in grid-index order (or, for the merged polygon rows of
``tree_rows.RowMerger``, in ascending longitude order, which is the order their results come back
in).  Nothing is held per point: one index array per leaf is unmapped, and the rows are concatenated
with numpy.
"""

import numpy as np

from .tensor_index_tree import BulkGridTensorIndexNode

__all__ = ["fold_into_bulk_grid"]


def _leaf_indexes(datacube, lon_child, leaf_path):
    """The grid indexes of one longitude leaf, in the order its values are stored."""
    key_value_path = {lon_child.axis.name: lon_child.values}
    leaf_path["index"] = lon_child.indexes
    key_value_path, leaf_path, datacube.unwanted_path = lon_child.axis.unmap_path_key(
        key_value_path, leaf_path, datacube.unwanted_path
    )
    return np.asarray(key_value_path["values"], dtype=np.int64)


def _leaf_tags(lat_child, lon_child, order):
    """``(tag_sets, tag_ids)`` of one longitude leaf's points, reordered like its values.

    A leaf whose points carry different tags (the merged rows of a union of differently tagged shapes,
    see ``tree_rows.RowMerger``) keeps them per point; otherwise all of its points share the tags of
    the latitude and longitude nodes.
    """
    lat_tags = lat_child.tags
    if lon_child.tag_ids is None:
        return [frozenset(lat_tags | lon_child.tags)], None
    tag_sets = [frozenset(lat_tags | tags) for tags in lon_child.tag_sets]
    tag_ids = lon_child.tag_ids if order is None else lon_child.tag_ids[order]
    return tag_sets, tag_ids


def _row_leaves(datacube, lat_child, leaf_path):
    """``(values, indexes, tag_sets, tag_ids)`` per longitude leaf of one latitude node, in tree order."""
    key_value_path = {lat_child.axis.name: lat_child.values}
    key_value_path, leaf_path, datacube.unwanted_path = lat_child.axis.unmap_path_key(
        key_value_path, leaf_path, datacube.unwanted_path
    )
    leaf_path.update(key_value_path)
    leaves = []
    for lon_child in lat_child.children:
        indexes = _leaf_indexes(datacube, lon_child, leaf_path)
        values = np.asarray(lon_child.values, dtype=np.float64)
        order = None
        if not lon_child._keep_value_order and indexes.size > 1:
            # a box leaf's points come back in grid-index order, as ``prepare`` leaves its values
            order = np.argsort(indexes, kind="stable")
            if np.array_equal(order, np.arange(indexes.size)):
                order = None
            else:
                indexes = indexes[order]
                values = values[order]
        tag_sets, tag_ids = _leaf_tags(lat_child, lon_child, order)
        leaves.append((values, indexes, tag_sets, tag_ids))
    return leaves


def _unique_first_seen(indexes):
    """Positions of the first occurrence of each index, ascending, or None if there are no duplicates."""
    if indexes.size < 2:
        return None
    _, first = np.unique(indexes, return_index=True)
    if first.size == indexes.size:
        return None
    first.sort()
    return first


def fold_into_bulk_grid(datacube, requests, leaf_path):
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

    lat_values = []
    row_lengths = []
    values = []
    indexes = []
    tag_id_blocks = []
    tag_sets = []
    ids_of = {}

    def tag_id(tags):
        found = ids_of.get(tags)
        if found is None:
            found = ids_of[tags] = len(tag_sets)
            tag_sets.append(tags)
        return found

    for lat_child in requests.children:
        row_length = 0
        for leaf_values, leaf_indexes, leaf_tag_sets, leaf_tag_ids in _row_leaves(datacube, lat_child, leaf_path):
            if leaf_values.size == 0:
                continue
            ids = np.asarray([tag_id(tags) for tags in leaf_tag_sets], dtype=np.int32)
            values.append(leaf_values)
            indexes.append(leaf_indexes)
            if leaf_tag_ids is None:
                tag_id_blocks.append(np.broadcast_to(ids, (leaf_values.size,)))
            else:
                tag_id_blocks.append(ids[leaf_tag_ids])
            row_length += leaf_values.size
        if row_length != 0:
            lat_values.append(lat_child.values[0])
            row_lengths.append(row_length)

    for lat_child in list(requests.children):
        requests.children.remove(lat_child)
        lat_child._parent = None
    if len(lat_values) == 0:
        requests.remove_branch()
        return None

    lat_values = np.asarray(lat_values, dtype=np.float64)
    row_lengths = np.asarray(row_lengths, dtype=np.int64)
    lon_values = np.concatenate(values) if len(values) > 1 else values[0]
    del values
    all_indexes = np.concatenate(indexes) if len(indexes) > 1 else indexes[0]
    del indexes
    tag_ids = np.concatenate(tag_id_blocks) if len(tag_id_blocks) > 1 else np.asarray(tag_id_blocks[0])
    del tag_id_blocks

    keep = _unique_first_seen(all_indexes)
    if keep is not None:
        # a point reached from two rows (eg. a box overlapping itself across the longitude seam) is
        # kept where it was first seen, as the per-row planning does
        row_of_point = np.searchsorted(np.cumsum(row_lengths), keep, side="right")
        row_lengths = np.bincount(row_of_point, minlength=row_lengths.size)
        kept_rows = row_lengths > 0
        lat_values = lat_values[kept_rows]
        row_lengths = row_lengths[kept_rows]
        lon_values = lon_values[keep]
        all_indexes = all_indexes[keep]
        tag_ids = tag_ids[keep]

    coordinates = np.column_stack((np.repeat(lat_values, row_lengths), lon_values))
    del lon_values
    grid_node = BulkGridTensorIndexNode(
        [lat_ax, lon_ax],
        lat_values,
        None,
        all_indexes,
        tag_ids=tag_ids,
        tag_sets=tag_sets,
        row_lengths=row_lengths,
        coordinates=coordinates,
    )
    requests.add_child(grid_node)
    return grid_node
