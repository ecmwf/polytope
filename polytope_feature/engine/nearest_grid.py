"""Resolve many nearest-point queries on a structured grid in one pass.

A nearest ``Point`` on the two mapped axes of a structured grid (``latitude``, ``longitude``) used to be
resolved in two steps, once per query point: ``Polytope.slice`` descended the whole tree prefix for that
point and sliced out its (at most four) bracketing grid points, and ``FDBDatacube.nearest_lat_lon_search``
then rebuilt and sorted *every* candidate of the request to pick the one nearest to it.  That second step
is O(N^2) in the number of query points: 2.3 s for 1 000 points on O1280, 420 s for 10 000, hours for
100 000.

Here all queries of one tree prefix are resolved together, in O(N log n_grid): the bracketing grid rows of
every query come from one ``searchsorted`` over the mapper's row latitudes, the bracketing longitudes from
one ``searchsorted`` per grid row touched (all queries of that row at once), and the nearest of the at most
four candidates is picked in numpy.  The resolved points become one array-backed
:class:`~polytope_feature.datacube.tensor_index_tree.BulkGridTensorIndexNode` -- the node
``FDBDatacube.prepare`` folds the sliced latitude/longitude layers into anyway -- so nothing downstream
changes and ``nearest_lat_lon_search`` never runs.

The values the node holds are the ones the old path produced, bit for bit:

* a candidate longitude is ``round(grid longitude + offset, 12)`` and is then mapped back into the cyclic
  axis range and rounded again, which is what ``DatacubeAxisCyclic.find_indices_between`` followed by
  ``HullSlicer.remap_values`` does to it.  The rounding is Python's ``round``, not ``numpy.round``: the two
  disagree in the 12th decimal for about one O1280 longitude in 70, and a coordinate that differs in the
  12th decimal is a different coverage in the output;
* the points come out in the order the fold produced them: grid rows by ascending latitude, and within a
  row by ascending longitude when the slicer merges union rows (``tree_rows.RowMerger``, which is what
  polytope-mars uses) or by grid index otherwise -- on a HEALPix nested grid the two differ;
* several queries whose nearest point is the same grid point still produce that point once (the request
  then has fewer points than it asked for; see ``point_of_query`` below).

One thing is deliberately *not* reproduced.  The old search handed ``nearest_pt`` the whole candidate tree,
so every query was matched against the candidates of every *other* query too and could be resolved onto a
grid point outside its own bracket -- which point a query got depended on the other points in the request.
Here each query is resolved against its own bracket.  The two can only differ where a row's longitude
spacing is wider than the latitude spacing of the rows bracketing the query, i.e. in the polar caps of a
reduced grid (the first O1280 row has 20 points, 18 degrees apart), and then only when another query of the
same request happens to bracket a nearby row.

The node carries ``point_of_query``: for every query point, in request order, the index of the point of the
node it resolved to.  Nothing in polytope-feature reads it; it is the mapping a caller needs to report one
coverage per *requested* point even where several requested points collapsed onto one grid point.
"""

import logging
import math

import numpy as np

from ..datacube.tensor_index_tree import BulkGridTensorIndexNode
from ..datacube.transformations.datacube_cyclic.datacube_cyclic import (
    DatacubeAxisCyclic,
)
from ..datacube.transformations.datacube_mappers.datacube_mappers import DatacubeMapper
from ..datacube.transformations.datacube_reverse.datacube_reverse import (
    DatacubeAxisReverse,
)

__all__ = [
    "batched_axes",
    "batched_polytopes",
    "batches_point",
    "batches_polytope",
    "build_bulk_node",
    "resolve",
]

#: Transformations on the spatial axes whose effect on the sliced values this module reproduces.
_KNOWN_TRANSFORMATIONS = (DatacubeMapper, DatacubeAxisCyclic, DatacubeAxisReverse)


# ---------------------------------------------------------------------------------------------------------------------
# Can this datacube's nearest queries be batched?


def _structured_mapper(datacube):
    mapper = getattr(datacube, "grid_transformation", None)
    if mapper is None or getattr(mapper, "is_irregular", True):
        return None
    return mapper


def _cyclic_of(axis):
    cyclic = [t for t in axis.transformations if isinstance(t, DatacubeAxisCyclic)]
    return cyclic[0] if len(cyclic) == 1 else None


def _known_transformations(axis, allowed):
    return all(isinstance(t, _KNOWN_TRANSFORMATIONS) and isinstance(t, allowed) for t in axis.transformations)


def _compute_batched_axes(datacube, api):
    mapper = _structured_mapper(datacube)
    if mapper is None:
        return None
    names = tuple(mapper._mapped_axes())
    if len(names) != 2:
        return None
    axes = datacube.axes
    if axes is None or any(name not in axes for name in names):
        return None
    lat_ax, lon_ax = (axes[name] for name in names)
    if api is not None and any(api.engine_options.get(name) != "hullslicer" for name in names):
        return None
    if any(name in datacube.complete_axes for name in names):
        # the bracket formulas below are those of a mapped (fake) axis, not of a pandas index
        return None
    if not _known_transformations(lat_ax, (DatacubeMapper, DatacubeAxisReverse)):
        return None
    if not _known_transformations(lon_ax, (DatacubeMapper, DatacubeAxisCyclic)):
        return None
    rows = mapper.first_axis_vals()
    if len(rows) == 0:
        return None
    # A grid whose rows run from north to south is read through the reverse transformation; one without it
    # would be searched by the ascending formula and find nothing.
    if (rows[0] > rows[-1]) != bool(getattr(lat_ax, "reorder", False)):
        return None
    return names


def batched_axes(datacube, api=None):
    """The ``(first, second)`` axis names whose nearest queries this module resolves, or None.

    None for a datacube without a structured grid mapper (a point cloud, an xarray datacube) and for one
    whose spatial axes carry transformations whose effect on the sliced values is not reproduced here; the
    caller then keeps the per-query path.  Computed once per datacube.
    """
    cached = getattr(datacube, "_nearest_grid_axes", None)
    if cached is None:
        cached = datacube._nearest_grid_axes = (_compute_batched_axes(datacube, api),)
    return cached[0]


def _is_nearest_query(method, k, axes, names):
    return method == "nearest" and k == 1 and names is not None and len(axes) == 2 and set(axes) == set(names)


def batches_polytope(polytope, datacube, api=None):
    """Whether ``polytope`` is a nearest query this module resolves instead of the slicer."""
    return _is_nearest_query(polytope.method, polytope.k, polytope.axes(), batched_axes(datacube, api))


def batches_point(shape, datacube, api=None):
    """Whether a ``Point`` shape's values are nearest queries this module resolves.

    Such a point must stay two-dimensional (``decompose_1D = False``) so that each of its values reaches
    the engine as one polytope with both coordinates, as it does for the quadtree slicer.
    """
    return _is_nearest_query(shape.method, shape.k, shape.axes(), batched_axes(datacube, api))


def batched_polytopes(node, ax, datacube, api):
    """The nearest queries of ``node`` to resolve on axis ``ax``, in request order (empty when there are none).

    They are resolved on the first of the two spatial axes, which is where the engine reaches them with the
    tree prefix built: the second axis then has no nodes left to descend into.
    """
    names = batched_axes(datacube, api)
    if names is None or ax.name != names[0]:
        return ()
    return [p for p in getattr(node, "batched_polytopes", ()) if batches_polytope(p, datacube, api)]


# ---------------------------------------------------------------------------------------------------------------------
# The vectorised search


def _round_values(values, decimals):
    """``round(v, decimals)`` of every value, as Python's ``round`` does it.

    ``numpy.round`` is not the same function: it scales by a power of ten, rounds and scales back, and the
    double it lands on differs from the correctly rounded decimal for about 1.5% of the longitudes of an
    O1280 grid.  Those differences are 1e-12 in a coordinate that is written out, so they matter.
    """
    values = np.asarray(values, dtype=np.float64)
    return np.fromiter((round(v, decimals) for v in values.tolist()), dtype=np.float64, count=values.size)


class _CyclicLongitude:
    """The cyclic longitude axis arithmetic of one request, vectorised over its query points.

    Reproduces, for a query point, what ``DatacubeAxisCyclic`` does to a one-point range on the longitude
    axis: the range searched on a grid row (``search_range``), the offset added back to the values found
    (``offset``) and the mapping of a value back into the axis range (``canonical``).
    """

    def __init__(self, axis):
        self.axis = axis
        self.tol = axis.tol
        self.decimals = int(-math.log10(axis.tol)) if axis.can_round else None
        cyclic = _cyclic_of(axis)
        self.cyclic = cyclic is not None
        self.lower, self.upper = (cyclic.range[0], cyclic.range[1]) if cyclic is not None else (0.0, 0.0)
        self.span = self.upper - self.lower

    def canonical(self, values):
        """``DatacubeAxisCyclic._remap_val_to_axis_range`` of every value."""
        if not self.cyclic:
            return np.asarray(values, dtype=np.float64)
        values = np.asarray(values, dtype=np.float64)
        below = values < self.lower
        above = values >= self.upper
        out = values.copy()
        # int() of the loop count truncates towards zero, which np.trunc does and np.floor does not
        loops = np.trunc((self.lower - values[below] - self.tol) / self.span)
        out[below] = values[below] + (loops + 1) * self.span
        loops = np.trunc((values[above] - self.upper) / self.span)
        out[above] = values[above] - (loops + 1) * self.span
        return out

    def search_range(self, queries):
        """``(low, up, offset)`` of the range searched on a grid row for every query longitude."""
        low = queries - self.tol
        up = queries + self.tol
        if not self.cyclic:
            return low, up, np.zeros(queries.shape, dtype=np.float64)
        # a range inside the axis range is searched as it is; one outside it is searched around its
        # canonical lower end, and the offset is put back onto the values found
        inside = (low >= self.lower - self.tol) & (low <= self.upper + self.tol)
        inside &= (up >= self.lower - self.tol) & (up <= self.upper + self.tol)
        canonical_low = self.canonical(low)
        search_low = np.where(inside, low, canonical_low - self.tol)
        search_up = np.where(inside, up, canonical_low + self.tol)
        unpadded = low + 1.5 * self.tol
        return search_low, search_up, unpadded - self.canonical(unpadded)

    def stored_values(self, values, offsets):
        """The values a slicer would store for the grid longitudes ``values`` found with ``offsets``."""
        found = np.asarray(values, dtype=np.float64) + offsets
        if self.decimals is not None:
            found = _round_values(found, self.decimals)
        if self.span is None:
            return found
        outside = (found < self.lower - self.tol) | (found > self.upper + self.tol) | (found == self.upper)
        if not outside.any():
            return found
        remapped = self.canonical(found[outside])
        found[outside] = remapped if self.decimals is None else _round_values(remapped, self.decimals)
        return found


def _concatenated_ranges(starts, counts):
    """``concatenate([arange(s, s + c) for s, c in zip(starts, counts)])`` without a Python loop."""
    total = int(counts.sum())
    out = np.ones(total, dtype=np.int64)
    ends = np.cumsum(counts)
    out[0] = starts[0]
    out[ends[:-1]] = starts[1:] - (starts[:-1] + counts[:-1]) + 1
    return np.cumsum(out)


def _row_brackets(rows, queries, tol, descending):
    """The grid rows bracketing every query latitude: ``(start, stop)`` index arrays into ``rows``.

    The same rows ``find_indices_between`` with ``method="nearest"`` returns: the values between
    ``query - tol`` and ``query + tol`` widened by one row on each side, which for a single point is the row
    above and the row below it (one row at the poles, three when the query sits on a row).
    """
    n = rows.size
    if descending:
        # rows descend, so -rows ascends and searchsorted counts the rows above a latitude
        above = np.searchsorted(-rows, -(queries + tol), side="left")
        below = np.searchsorted(-rows, -(queries - tol), side="left")
        return np.maximum(above - 1, 0), np.minimum(below + 1, n)
    start = np.searchsorted(rows, queries - tol, side="left")
    stop = np.searchsorted(rows, queries + tol, side="right")
    return np.maximum(start - 1, 0), np.minimum(stop + 1, n)


def _candidates(mapper, rows, row_lons, lon_axis, queries, row_start, row_count):
    """Every (query, grid point) candidate pair of the request.

    Returns ``(query, row, longitude index, stored longitude)`` arrays: for each query, the bracketing
    longitudes on each of its bracketing rows.  The rows are visited once each, with all of their queries
    at once, so no row's longitudes are built more than once and nothing is held per candidate but the
    result.
    """
    query_of = np.repeat(np.arange(queries.size, dtype=np.int64), row_count)
    row_of = _concatenated_ranges(row_start, row_count)
    order = np.argsort(row_of, kind="stable")
    query_of, row_of = query_of[order], row_of[order]
    cuts = np.flatnonzero(np.diff(row_of)) + 1

    search_low, search_up, offsets = lon_axis.search_range(queries)
    out_query, out_row, out_index, out_lon = [], [], [], []
    for first, last in zip(np.r_[0, cuts], np.r_[cuts, row_of.size]):
        row = int(row_of[first])
        queries_here = query_of[first:last]
        lons = row_lons(row)
        start = np.maximum(np.searchsorted(lons, search_low[queries_here], side="left") - 1, 0)
        stop = np.minimum(np.searchsorted(lons, search_up[queries_here], side="right") + 1, lons.size)
        count = stop - start
        index = _concatenated_ranges(start, count)
        picked = np.repeat(queries_here, count)
        out_query.append(picked)
        out_row.append(np.full(index.size, row, dtype=np.int64))
        out_index.append(index)
        out_lon.append(lon_axis.stored_values(lons[index], offsets[picked]))
    return (
        np.concatenate(out_query),
        np.concatenate(out_row),
        np.concatenate(out_index),
        np.concatenate(out_lon),
    )


def _nearest_of(query_of, n_queries, distances, latitudes, longitudes):
    """The candidate nearest to each query: the first minimum in (latitude, longitude) order, as the
    per-query sort by distance of ``utility.geometry.nearest_pt`` picked it."""
    by_point = np.lexsort((longitudes, latitudes))
    by_query = np.lexsort((distances[by_point], query_of[by_point]))
    chosen = by_point[by_query]
    first = np.r_[0, np.flatnonzero(np.diff(query_of[chosen])) + 1]
    assert first.size == n_queries
    return chosen[first]


class NearestPoints:
    """The resolved points of one batched nearest search, in the order a prepared tree holds them.

    ``row_latitudes`` are the latitudes of the grid rows that hold points, ascending; ``row_lengths`` the
    number of points each contributes; ``longitudes`` and ``indexes`` the points of all rows concatenated,
    in output order.  ``point_of_query`` gives, per query point in request order, the index of the point it
    resolved to (several queries share a point when they are nearest to the same grid point).
    """

    __slots__ = ("row_latitudes", "row_lengths", "longitudes", "indexes", "point_of_query")

    def __init__(self, row_latitudes, row_lengths, longitudes, indexes, point_of_query):
        self.row_latitudes = row_latitudes
        self.row_lengths = row_lengths
        self.longitudes = longitudes
        self.indexes = indexes
        self.point_of_query = point_of_query

    @property
    def point_count(self):
        return self.longitudes.size

    def coordinates(self):
        return np.column_stack((np.repeat(self.row_latitudes, self.row_lengths), self.longitudes))

    def point_tags(self, tags):
        """One set of tags per point: the tags of the queries that resolved to it, or None when untagged."""
        if all(tag is None for tag in tags):
            return None
        per_point = [set() for _ in range(self.point_count)]
        for tag, point in zip(tags, self.point_of_query.tolist()):
            if tag is not None:
                per_point[point].add(tag)
        return per_point


def resolve(datacube, lat_ax, lon_ax, queries, keep_value_order=False):
    """The nearest grid point of every query, as a :class:`NearestPoints`.

    ``queries`` is an (N, 2) array of (first axis, second axis) values in request order.
    ``keep_value_order`` orders the points of a row by ascending longitude instead of by grid index, which
    is what the merged union rows of ``tree_rows.RowMerger`` do to a sliced tree.
    """
    mapper = datacube.grid_transformation
    queries = np.asarray(queries, dtype=np.float64).reshape(-1, 2)
    rows = np.asarray(mapper.first_axis_vals(), dtype=np.float64)
    descending = rows.size > 1 and rows[0] > rows[-1]
    row_start, row_stop = _row_brackets(rows, queries[:, 0], lat_ax.tol, descending)
    lat_decimals = int(-math.log10(lat_ax.tol)) if lat_ax.can_round else None
    row_latitudes = rows if lat_decimals is None else _round_values(rows, lat_decimals)

    def row_lons(row):
        return np.asarray(mapper.second_axis_vals((rows[row],)), dtype=np.float64)

    lon_axis = _CyclicLongitude(lon_ax)
    query_of, row_of, index_of, lon_of = _candidates(
        mapper, rows, row_lons, lon_axis, queries[:, 1], row_start, row_stop - row_start
    )
    lat_of = row_latitudes[row_of]

    # the distance the per-query search minimised: the query longitude in the axis range, the candidate as
    # the tree stores it
    query_lat = queries[:, 0]
    query_lon = lon_axis.canonical(queries[:, 1])
    d_lat = lat_of - query_lat[query_of]
    d_lon = lon_of - query_lon[query_of]
    chosen = _nearest_of(query_of, queries.shape[0], d_lat * d_lat + d_lon * d_lon, lat_of, lon_of)

    return _points_of(mapper, rows, row_of[chosen], index_of[chosen], lat_of[chosen], lon_of[chosen], keep_value_order)


def _points_of(mapper, rows, row_of_query, index_of_query, lat_of_query, lon_of_query, keep_value_order):
    """The chosen candidates as the points of a prepared tree: de-duplicated, row by row, in output order."""
    # grid rows by ascending latitude, longitudes ascending within a row: the order the slicer's sorted
    # nodes and sorted leaf values gave the fold
    order = np.lexsort((lon_of_query, lat_of_query))
    sorted_lat, sorted_lon = lat_of_query[order], lon_of_query[order]
    new_point = np.ones(order.size, dtype=bool)
    new_point[1:] = (sorted_lat[1:] != sorted_lat[:-1]) | (sorted_lon[1:] != sorted_lon[:-1])
    point_of_sorted = np.cumsum(new_point) - 1
    point_of_query = np.empty(order.size, dtype=np.int64)
    point_of_query[order] = point_of_sorted

    first = np.flatnonzero(new_point)
    latitudes, longitudes = sorted_lat[first], sorted_lon[first]
    rows_of_point = row_of_query[order][first]
    new_row = np.ones(first.size, dtype=bool)
    new_row[1:] = rows_of_point[1:] != rows_of_point[:-1]
    row_first = np.flatnonzero(new_row)
    row_lengths = np.diff(np.r_[row_first, first.size])

    indexes = np.empty(first.size, dtype=np.int64)
    final_position = np.empty(first.size, dtype=np.int64)
    for row, at, length in zip(rows_of_point[row_first], row_first, row_lengths):
        where = slice(int(at), int(at + length))
        row_indexes = np.asarray(
            mapper.unmap((rows[row],), longitudes[where].tolist()),
            dtype=np.int64,
        )
        position = np.arange(at, at + length, dtype=np.int64)
        if not keep_value_order and length > 1:
            by_index = np.argsort(row_indexes, kind="stable")
            row_indexes = row_indexes[by_index]
            longitudes[where] = longitudes[where][by_index]
            position[by_index] = position
        indexes[where] = row_indexes
        final_position[where] = position
    return NearestPoints(
        latitudes[row_first],
        row_lengths,
        longitudes,
        indexes,
        final_position[point_of_query],
    )


# ---------------------------------------------------------------------------------------------------------------------
# The node the engine builds


def build_bulk_node(node, polytopes, datacube, api):
    """Resolve ``polytopes`` (nearest queries) and give ``node`` one bulk grid child holding their points.

    One node per tree prefix: the search itself is independent of the prefix, so it is run once per
    ``Polytope.slice`` and its arrays are shared by the prefixes of the same request (a request with
    several parameters or levels descends to several spatial nodes).
    """
    names = batched_axes(datacube, api)
    assert names is not None, "nearest queries were batched on a datacube that cannot batch them"
    lat_ax, lon_ax = (datacube.axes[name] for name in names)
    reversed_axes = tuple(polytopes[0].axes()) != tuple(names)
    queries = np.asarray([polytope.points[0] for polytope in polytopes], dtype=np.float64)
    if reversed_axes:
        queries = queries[:, ::-1]
    tags = [polytope.tag for polytope in polytopes]

    engine = api.find_engine(lat_ax)
    cached = getattr(engine, "_nearest_points", None)
    key = tuple(id(polytope) for polytope in polytopes)
    if cached is None or cached[0] != key:
        logging.debug("Resolving %d nearest points on the %s grid", len(polytopes), datacube.grid_md5_hash)
        points = resolve(datacube, lat_ax, lon_ax, queries, keep_value_order=getattr(api, "merge_leaf_rows", False))
        cached = (key, points, points.point_tags(tags))
        engine._nearest_points = cached
    _, points, point_tags = cached

    if points.point_count == 0:
        node.remove_branch()
        return None
    grid_node = BulkGridTensorIndexNode(
        [lat_ax, lon_ax],
        points.row_latitudes,
        None,
        points.indexes,
        point_tags=point_tags,
        row_lengths=points.row_lengths,
        coordinates=points.coordinates(),
    )
    grid_node.point_of_query = points.point_of_query
    node.add_child(grid_node)
    return grid_node
