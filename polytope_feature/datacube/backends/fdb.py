import logging
import time
from copy import deepcopy
from itertools import product

import numpy as np

from ...utility.exceptions import BadGridError, BadRequestError, GribJumpNoIndexError
from ...utility.geometry import nearest_pt
from ..tensor_index_tree import (
    BulkGridTensorIndexNode,
    BulkMergedTensorIndexNode,
)
from ..tree_fold import fold_into_bulk_grid
from ..tree_values import is_array, values_hash_key
from .datacube import Datacube, TensorIndexTree


def field_values_flat(result):
    """One field's values as a contiguous float64 array, or ``None`` when gribjump had no data for the field.

    Prefers pygribjump's ``values_flat`` (a view over the whole result, so no per-range objects are created) and
    falls back to concatenating ``values`` for result objects that do not have it.  On a HEALPix nested grid a
    bounding box asks for roughly one index range per 1.6 points, where the per-range ``values`` list costs a
    numpy object plus a list slot per range and the flat buffer costs eight bytes per value.  Bitmap-missing
    points are NaN in the buffer gribjump fills, exactly as they are in the per-range ``values`` views, which
    are slices of the same buffer; ``masks_flat`` is therefore not needed to reproduce them.
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


class BulkFDBDecoding:
    __slots__ = ("node", "sorted_output_positions")

    def __init__(self, node, sorted_output_positions):
        self.node = node
        self.sorted_output_positions = sorted_output_positions


class FDBDatacube(Datacube):
    def __init__(
        self,
        gj,
        config=None,
        axis_options=None,
        compressed_axes_options=[],
        alternative_axes=[],
        context=None,
        use_catalogue=False,
    ):
        self.use_catalogue = use_catalogue
        if config is None:
            config = {}
        if context is None:
            context = {}

        super().__init__(
            axis_options,
            compressed_axes_options,
        )

        logging.info("Created an FDB datacube with options: " + str(axis_options))

        self.unwanted_path = {}
        self.axis_options = axis_options
        # The spatial layers of a prepared tree are always folded into one array-backed node per
        # spatial sub-tree (see :meth:`prepare`).  Kept as an attribute because the slicers read it.
        self.bulk_grid_leaves = True

        partial_request = config
        # Find values in the level 3 FDB datacube

        self.gj = gj
        if len(alternative_axes) == 0:
            if self.use_catalogue:
                from .catalogue_helper import find_axes_from_qube

                logging.info("Find GribJump axes for %s from catalogue", context)
                self.fdb_coordinates = find_axes_from_qube(partial_request)
                logging.info("Retrieved available GribJump axes for %s", context)
            else:
                logging.info("Find GribJump axes for %s", context)
                self.fdb_coordinates = self.gj.axes(partial_request, ctx=context)
                logging.info("Retrieved available GribJump axes for %s", context)
                if len(self.fdb_coordinates) == 0 or set(partial_request) > set(self.fdb_coordinates):
                    raise BadRequestError(partial_request)
        else:
            self.fdb_coordinates = {}
            for axis_config in alternative_axes:
                self.fdb_coordinates[axis_config.axis_name] = axis_config.values

        fdb_coordinates_copy = deepcopy(self.fdb_coordinates)
        for axis, vals in fdb_coordinates_copy.items():
            if len(vals) == 1:
                if vals[0] == "":
                    self.fdb_coordinates.pop(axis)

        logging.info("Axes returned from GribJump are: " + str(self.fdb_coordinates))

        self.fdb_coordinates["values"] = []
        for name, values in self.fdb_coordinates.items():
            values.sort()
            options = None
            for opt in self.axis_options:
                if opt.axis_name == name:
                    options = opt

            self._check_and_add_axes(options, name, values)
            self.treated_axes.append(name)
            self.complete_axes.append(name)

        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in self.treated_axes:
                options = None
                for opt in self.axis_options:
                    if opt.axis_name == name:
                        options = opt

                val = self._axes[name].type
                self._check_and_add_axes(options, name, val)

        logging.info("Polytope created axes for: " + str(self._axes.keys()))

    def find_point_cloud(self):
        # find the point cloud of irregular grid if it exists
        if self.grid_transformation.is_irregular:
            return self.grid_transformation._final_transformation.grid_latlon_points()

    def check_branching_axes(self, request):
        polytopes = request.polytopes()
        for polytope in polytopes:
            for ax in polytope._axes:
                if ax == "levtype":
                    upper, lower, idx = polytope.extents(ax)
                    if "sfc" in polytope.points[idx]:
                        self.fdb_coordinates.pop("levelist", None)

                if ax == "param":
                    upper, lower, idx = polytope.extents(ax)
                    if "140251" not in polytope.points[idx]:
                        self.fdb_coordinates.pop("direction", None)
                        self.fdb_coordinates.pop("frequency", None)
                    else:
                        # special param with direction and frequency
                        if len(polytope.points[idx]) > 1:
                            raise ValueError(
                                "Param 140251 is part of a special branching of the datacube. Please request it separately."  # noqa: E501
                            )
                if ax == "stream":
                    upper, lower, idx = polytope.extents(ax)
                    if "clmn" not in polytope.points[idx]:
                        self.fdb_coordinates.pop("year", None)
                        self.fdb_coordinates.pop("month", None)
                    else:
                        if len(polytope.points[idx]) > 1:
                            raise ValueError(
                                "Stream clmn is part of a special branching of the datacube. Please request it separately."  # noqa: E501
                            )
        self.fdb_coordinates.pop("quantile", None)

        # NOTE: verify that we also remove the axis object for axes we've removed here
        axes_to_remove = set(self.complete_axes) - set(self.fdb_coordinates.keys())

        # Remove the keys from self._axes
        for axis_name in axes_to_remove:
            self._axes.pop(axis_name, None)

    def prepare(self, requests: TensorIndexTree, context=None, select=None, latitude_range=None):
        """Put ``requests`` into the point order ``get`` returns, without fetching any data.

        Runs every step of :meth:`get` before the gribjump call: optional pruning (``select`` / ``latitude_range``,
        as in ``get``), nearest-point selection, conversion of each leaf's coordinates to grid indices, dropping
        duplicate grid points (e.g. a box that overlaps itself across the longitude seam) and reordering each
        longitude leaf's ``values`` by grid index (HEALPix nested and other grids number points differently from
        slice order).  ``gribjump.extract`` is not called and every ``result`` is left untouched.  The merged polygon
        rows of ``Polytope._merge_union_rows`` keep their ascending values: ``get`` returns their results in that order,
        as it did for the per-point leaves of a polygon.

        Use it to read the final coordinate list of a request before extracting any values: after ``prepare``
        the latitude/longitude values in the tree are exactly those (and in the order) that ``get`` fills, and
        ``latitude_point_counts`` counts the points ``get`` returns per latitude node.

        Like ``get``, the tree is modified in place and returned when neither ``select`` nor ``latitude_range``
        is given; otherwise a pruned copy is prepared and returned and ``requests`` is left untouched.
        ``prepare`` is idempotent, and ``get`` on a prepared tree, or on ``prepared.prune(select, latitude_range)``,
        gives the same ``values`` and ``result`` order as ``get`` on the unprepared tree (bands of a prepared tree
        concatenate to the full result).  Grid indices are not cached: ``get`` recomputes them for the (sub-)tree it
        fetches, which keeps the tree at ~8 B/point.
        """
        requests = self._prune_for_get(requests, select, latitude_range)
        if len(requests.children) != 0:
            self._gribjump_requests(requests)
        return requests

    def get(self, requests: TensorIndexTree, context=None, select=None, latitude_range=None):
        """Fetch data from gribjump into the leaves of ``requests``; return the tree holding the results.

        ``requests`` may be a full tree from ``Polytope.slice``, a sub-tree from ``TensorIndexTree.prune``, or
        either of those after :meth:`prepare`.  Passing ``select`` and/or ``latitude_range`` prunes ``requests``
        first (see ``TensorIndexTree.prune``) and fills and returns the pruned copy, leaving ``requests`` untouched.
        Results for a pruned tree are exactly the corresponding slice of a full ``get``: the compressed axes expand
        to the selected values only, point order within a band is the same, and a field gribjump does not have
        yields ``None`` values.  ``get`` keeps no state between calls, so pruned trees of the same parent can be
        fetched one after another.

        After ``get`` each leaf's ``result`` is a ``np.ndarray``: float64 when every field was found, otherwise
        object dtype with ``None`` for the missing values (use ``leaf.result_array()`` for float64 with NaN).
        Leaf ``values`` are reordered by grid index and de-duplicated in place to line up with ``result`` (a no-op
        on a prepared tree; use :meth:`prepare` to get the final coordinates before fetching).
        Latitude bands are not supported together with nearest-point search, which selects among the points
        present in the tree being fetched.
        """
        if context is None:
            context = {}
        requests = self._prune_for_get(requests, select, latitude_range)
        if len(requests.children) == 0:
            return requests
        complete_list_complete_uncompressed_requests, complete_fdb_decoding_info = self._gribjump_requests(requests)
        iterator = self._gribjump_extract(complete_list_complete_uncompressed_requests, context)
        assignment_start = time.perf_counter()
        self.assign_fdb_output_to_nodes(iterator, complete_fdb_decoding_info)
        self.prototype_metrics["iterator_and_assignment_s"] = time.perf_counter() - assignment_start
        return requests

    def get_iter(self, requests: TensorIndexTree, context=None, select=None, latitude_range=None):
        """Fetch ``requests`` field by field, yielding ``(field_path, leaf_values)`` instead of filling the tree.

        Builds exactly the same gribjump call as :meth:`get` (same pruning, same requests, same order) but hands
        each field's values to the caller as they arrive, so that only one field need be alive at a time.  Each
        item is:

        * ``field_path``: the MARS keys of one field, as given to gribjump -- one scalar value per key, the keys
          in the order the tree descends (outermost axis first);
        * ``leaf_values``: ``[(bulk node, values), ...]``, one entry per spatial sub-tree of the field in tree
          order, ``values`` a fresh float64 array of the node's points in its point order (NaN where a point is
          bitmap-missing).  Concatenating them in order gives the field's points in the order ``get`` writes
          them into the nodes.  It is ``None`` when gribjump has no message for the field (what ``get`` records
          as ``None`` values), so that a caller can detect a missing field without reading any value.

        Items come in gribjump's request order: the spatial sub-trees in tree order and, within a sub-tree, its
        fields as the cartesian product of the compressed axes' values in tree order -- outermost axis first,
        innermost varying fastest (``itertools.product`` order, which is also the order ``get`` lays a leaf's
        fields out in its ``result``).  A field path appears once per sub-tree that holds points of it.

        Unlike ``get``, nothing is written to any ``result``: the tree is left as :meth:`prepare` leaves it (leaf
        values reordered by grid index and de-duplicated, every ``result`` untouched) and the caller owns the
        arrays it is given.  Nothing is requested until the first item is consumed.
        """
        if context is None:
            context = {}
        requests = self._prune_for_get(requests, select, latitude_range)
        if len(requests.children) == 0:
            return
        uncompressed_requests, decoding_info = self._gribjump_requests(requests)
        iterator = self._gribjump_extract(uncompressed_requests, context)
        for k, result in enumerate(iterator):
            decoding = decoding_info[k]
            values = self.bulk_field_values(result, decoding)
            del result
            yield uncompressed_requests[k][0], None if values is None else [(decoding.node, values)]
            del values  # let the caller's field go before the next one is read

    def _gribjump_extract(self, uncompressed_requests, context):
        if logging.root.level <= logging.DEBUG:
            printed_list_to_gj = uncompressed_requests[::1000]
            logging.debug("The requests we give GribJump are: %s", printed_list_to_gj)
        logging.info("Requests given to GribJump extract for %s", context)
        extract_start = time.perf_counter()
        try:
            iterator = self.gj.extract(uncompressed_requests, context)
            self.prototype_metrics["gj_extract_call_s"] = time.perf_counter() - extract_start
        except Exception as e:
            if "BadValue: Grid hash mismatch" in str(e):
                logging.info("Error is: %s", e)
                raise BadGridError()
            if "Missing JumpInfo" in str(e):
                logging.info("Error is: %s", e)
                raise GribJumpNoIndexError()
            else:
                raise e
        logging.info("Requests extracted from GribJump for %s", context)
        return iterator

    def _prune_for_get(self, requests: TensorIndexTree, select, latitude_range) -> TensorIndexTree:
        if select is None and latitude_range is None:
            return requests
        if latitude_range is not None and len(self.nearest_search) != 0:
            raise ValueError("latitude_range cannot be combined with nearest-point search")
        if latitude_range is not None and self.bulk_grid_leaves:
            raise ValueError(
                "latitude_range cannot be combined with bulk_grid_leaves: a field that fits the memory budget "
                "is fetched whole"
            )
        pruned = requests.prune(select=select, latitude_range=latitude_range)
        assert pruned is not None
        return pruned

    def _gribjump_requests(self, requests):
        """Build the gribjump extract requests for ``requests`` and their decoding info.

        One request per field of every spatial sub-tree, and one :class:`BulkFDBDecoding` per sub-tree,
        shared by all of its fields: it says which bulk node the values belong to and in which order.
        """
        # never carry unmapping state over from a previous get
        self.unwanted_path = {}
        self.prototype_metrics = {}
        self.prototype_metrics = {}
        fdb_requests = []
        fdb_requests_decoding_info = []
        planning_start = time.perf_counter()
        self.get_fdb_requests(requests, fdb_requests, fdb_requests_decoding_info)
        self.prototype_metrics["request_planning_s"] = time.perf_counter() - planning_start
        self.prototype_metrics["ranges_per_field"] = sum(len(request[1]) for request in fdb_requests)

        # expand the compressed non-spatial axes into one gribjump request per field
        complete_list_complete_uncompressed_requests = []
        complete_fdb_decoding_info = []
        for j, compressed_request in enumerate(fdb_requests):
            # find the possible combinations of compressed indices
            interm_branch_tuple_values = []
            for key in compressed_request[0].keys():
                interm_branch_tuple_values.append(compressed_request[0][key])
            n_fields = 1
            for branch_values in interm_branch_tuple_values:
                n_fields *= len(branch_values)
            # one bulk node holds the whole spatial selection; every field decodes the same way
            field_decodings = [fdb_requests_decoding_info[j]] * n_fields

            # Need to extract the possible requests and add them to the right nodes
            for field_index, combi in enumerate(product(*interm_branch_tuple_values)):
                uncompressed_request = {}
                for i, key in enumerate(compressed_request[0].keys()):
                    uncompressed_request[key] = combi[i]
                complete_uncompressed_request = (
                    uncompressed_request,
                    compressed_request[1],
                    self.grid_md5_hash,
                )
                complete_list_complete_uncompressed_requests.append(complete_uncompressed_request)
                complete_fdb_decoding_info.append(field_decodings[field_index])
        self.prototype_metrics["uncompressed_requests"] = len(complete_list_complete_uncompressed_requests)
        self.prototype_metrics["effective_range_arrays"] = sum(
            len(request[1]) for request in complete_list_complete_uncompressed_requests
        )
        return complete_list_complete_uncompressed_requests, complete_fdb_decoding_info

    def get_fdb_requests(
        self,
        requests: TensorIndexTree,
        fdb_requests=[],
        fdb_requests_decoding_info=[],
        leaf_path=None,
    ):
        """Descend ``requests`` and collect one ``(MARS path, index ranges)`` request per spatial sub-tree.

        Every spatial sub-tree is one array-backed node: either a bulk coupled-axis node, as the quadtree
        slicer builds it for an unstructured grid, or the latitude -> longitude layers of a structured grid
        folded into one node here (:func:`~polytope_feature.datacube.tree_fold.fold_into_bulk_grid`).
        """
        if leaf_path is None:
            leaf_path = {}

        if requests.axis.name == "root":
            logging.debug("Looking for data for the tree")
            for c in requests.children:
                self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info)
            return

        key_value_path = {requests.axis.name: requests.values}
        ax = requests.axis
        key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
        leaf_path.update(key_value_path)
        # Bulk coupled-axis leaves carry all selected canonical indexes in one array-backed node.
        if isinstance(requests.children[0], BulkMergedTensorIndexNode):
            for bulk_node in requests.children:
                path, ranges, decoding = self.get_bulk_merged_values(bulk_node, leaf_path)
                fdb_requests.append((path, ranges))
                fdb_requests_decoding_info.append(decoding)
        elif isinstance(requests.children[0].children[0], BulkMergedTensorIndexNode):
            for child in requests.children:
                self.get_fdb_requests(child, fdb_requests, fdb_requests_decoding_info, leaf_path)
        elif len(requests.children[0].children[0].children) == 0:
            # the last two layers of a structured grid: fold them into one node for the whole sub-tree
            if not isinstance(requests.children[0].children[0], TensorIndexTree):
                raise BadRequestError(
                    f"Spatial leaves of kind {type(requests.children[0].children[0]).__name__} cannot be "
                    "fetched: a spatial sub-tree is one array-backed node"
                )
            grid_node = fold_into_bulk_grid(self, requests, leaf_path)
            if grid_node is not None:
                path, ranges, decoding = self.get_bulk_merged_values(grid_node, leaf_path)
                fdb_requests.append((path, ranges))
                fdb_requests_decoding_info.append(decoding)
        # Otherwise remap the path for this key and iterate again over children
        else:
            for c in requests.children:
                self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info, leaf_path)

    def nearest_lat_lon_search(self, requests):
        if len(self.nearest_search) != 0:
            first_ax_name = requests.children[0].axis.name
            second_ax_name = requests.children[0].children[0].axis.name

            axes_in_nearest_search = [
                first_ax_name not in self.nearest_search.keys(),
                second_ax_name not in self.nearest_search.keys(),
            ]

            if all(not item for item in axes_in_nearest_search):
                raise Exception("nearest point search axes are wrong")

            second_ax = requests.children[0].children[0].axis

            nearest_pts_k = self.nearest_search.get((first_ax_name, second_ax_name), None)
            query_points = None
            if nearest_pts_k is not None:
                query_points = nearest_pts_k[0]
            else:
                nearest_pts_k = self.nearest_search.get((second_ax_name, first_ax_name), None)
                query_points = [[pt[1], pt[0]] for pt in nearest_pts_k[0]]
            query_tags = nearest_pts_k[2] if len(nearest_pts_k) > 2 else [None] * len(query_points)

            k = nearest_pts_k[1]
            if k != 1 and not self.grid_transformation.is_irregular:
                print("k nearest neighbour not supported in hullslicer, defaulting to nearest neighbour.")
                k = 1

            transformed_nearest_pts = []
            for point in query_points:
                transformed_nearest_pts.append([point[0], second_ax._remap_val_to_axis_range(point[1])])

            found_latlon_pts = []
            for lat_child in requests.children:
                for lon_child in lat_child.children:
                    found_latlon_pts.append([lat_child.values, lon_child.values])

            # now find the nearest lat lon to the points requested, remembering which query
            # point (and so which tag) each resolved point is nearest to
            nearest_latlons = []
            point_tags = {}
            for pt, tag in zip(transformed_nearest_pts, query_tags):
                nearest_latlon = nearest_pt(found_latlon_pts, pt, k)
                nearest_latlons.extend(nearest_latlon)
                for latlon in nearest_latlon:
                    tags = point_tags.setdefault(tuple(latlon), set())
                    if tag is not None:
                        tags.add(tag)
            nearest_tags = {tag for tag in query_tags if tag is not None}

            # need to remove the branches that do not fit
            lat_children_by_values = {child.values: child for child in requests.children}
            lat_children_values = list(lat_children_by_values.keys())
            for lat_child_val in lat_children_values:
                lat_child = lat_children_by_values[lat_child_val]
                if lat_child.values not in [(latlon[0],) for latlon in nearest_latlons]:
                    lat_child.remove_branch()
                else:
                    possible_lons = [latlon[1] for latlon in nearest_latlons if (latlon[0],) == lat_child.values]
                    lon_children_by_values = {values_hash_key(child.values): child for child in lat_child.children}
                    lon_children_values = list(lon_children_by_values.keys())
                    for lon_child_val in lon_children_values:
                        lon_child = lon_children_by_values[lon_child_val]
                        for value in lon_child.values:
                            if value not in possible_lons:
                                lon_child.remove_compressed_branch(value)
                    if lat_child.parent is not None:
                        self._retag_nearest_lons(lat_child, point_tags, nearest_tags)
            return point_tags
        return None

    @staticmethod
    def _retag_nearest_lons(lat_child, point_tags, nearest_tags):
        """Re-attach nearest-search tags to the points that are actually nearest to each query.

        While slicing, a nearest query's tag is stamped on every candidate it touches, so after
        the nearest search we drop those tags and give each resolved point the tags of the
        queries it is nearest to. A compressed longitude node carries one set of tags for all
        its values, so the longitude nodes of this latitude are rebuilt as one node per distinct
        set of tags (which also merges overlapping siblings coming from unions).  Array leaves
        (and their per-point tags, see ``tree_rows.RowMerger``) are rebuilt as array leaves.
        """
        lat_child.tags -= nearest_tags
        lat = lat_child.values[0]
        values_by_tags = {}
        lon_axis = None
        array_leaf = False
        keep_value_order = False
        for lon_child in list(lat_child.children):
            lon_axis = lon_child.axis
            array_leaf = array_leaf or is_array(lon_child.values)
            keep_value_order = keep_value_order or lon_child._keep_value_order
            node_tags = None if lon_child.tag_ids is not None else lon_child.tags - nearest_tags
            for i, value in enumerate(lon_child.values):
                base_tags = node_tags if node_tags is not None else lon_child.tags_of_point(i) - nearest_tags
                tags = frozenset(base_tags | point_tags.get((lat, value), set()))
                values_by_tags.setdefault(tags, set()).add(value)
        if lon_axis is None:
            return
        groups = list(values_by_tags.items())
        # Keep the existing node when it already holds a single group of values
        if len(groups) == 1 and len(lat_child.children) == 1:
            only_child = next(iter(lat_child.children))
            only_child.tag_ids = None
            only_child.tag_sets = None
            only_child.tags = set(groups[0][0])
            return
        for lon_child in list(lat_child.children):
            lat_child.children.remove(lon_child)
            lon_child._parent = None
        seen = set()
        for tags, values in groups:
            values = sorted(values - seen)
            seen.update(values)
            if len(values) == 0:
                continue
            node = TensorIndexTree(lon_axis, np.asarray(values, dtype=np.float64) if array_leaf else tuple(values))
            node.tags = set(tags)
            node._keep_value_order = keep_value_order
            lat_child.add_child(node)

    def get_bulk_merged_values(self, bulk_node, leaf_path=None):
        if leaf_path is None:
            leaf_path = {}

        if isinstance(bulk_node, BulkGridTensorIndexNode):
            # The grid node's indexes were already unmapped row by row when folding the tree
            path = deepcopy(leaf_path)
        else:
            lat_ax, lon_ax = bulk_node.axes
            first_coordinate = bulk_node.coordinates[0]

            # Run one representative point through the mapper to preserve its
            # generic path/unwanted-path semantics. Canonical indexes for all other
            # points are already carried by the bulk leaf.
            kv_lat = {lat_ax.name: first_coordinate[0]}
            kv_lat, leaf_path, self.unwanted_path = lat_ax.unmap_path_key(kv_lat, leaf_path, self.unwanted_path)
            leaf_path.update(kv_lat)
            kv_lon = {lon_ax.name: first_coordinate[1]}
            leaf_path["index"] = [int(bulk_node.indexes[0])]
            kv_lon, leaf_path, self.unwanted_path = lon_ax.unmap_path_key(kv_lon, leaf_path, self.unwanted_path)
            path = deepcopy(leaf_path)

        indexes = bulk_node.indexes
        # the field's ranges are the gaps in its sorted indexes; on a grid stored row by row the node's
        # points are already ascending, so neither the sort nor the un-sort on assignment is needed
        if len(indexes) < 2 or bool(np.all(np.diff(indexes) > 0)):
            sorted_output_positions = None
            sorted_indexes = indexes
        else:
            order = np.argsort(indexes, kind="stable")
            sorted_indexes = indexes[order]
            if len(indexes) <= np.iinfo(np.int32).max:
                order = order.astype(np.int32)
            sorted_output_positions = order
            del order
            if np.any(np.diff(sorted_indexes) == 0):
                raise ValueError("Bulk spatial selection contains duplicate canonical indexes")

        cuts = np.flatnonzero(np.diff(sorted_indexes) > 1)
        starts = np.r_[sorted_indexes[0], sorted_indexes[cuts + 1]]
        ends = np.r_[sorted_indexes[cuts] + 1, sorted_indexes[-1] + 1]
        ranges = [(int(start), int(end)) for start, end in zip(starts, ends)]

        path.pop("values", None)
        path.pop("index", None)
        return path, ranges, BulkFDBDecoding(bulk_node, sorted_output_positions)

    def assign_fdb_output_to_nodes(self, output_iterator, fdb_requests_decoding_info):
        """Append every field of the gribjump output to the bulk node it was requested for.

        Each result is consumed once, as one contiguous ``values_flat`` buffer scattered into the node's
        point order, so that nothing is kept per request range and no field's values outlive their result.
        """
        logging.debug("Assigning GribJump output to tree nodes")
        for k, result in enumerate(output_iterator):
            self.assign_bulk_result(result, fdb_requests_decoding_info[k])
        logging.debug("Finished assigning GribJump output to tree nodes")

    @staticmethod
    def bulk_field_values(result, decoding):
        """One field's values in a bulk node's point order, or ``None`` when gribjump had no message for it.

        The field is read once, as the contiguous ``values_flat`` buffer over all of its index ranges (in
        ascending grid-index order), and scattered back into the node's point order with the positions
        ``get_bulk_merged_values`` recorded when it sorted the node's indexes.
        """
        flat = field_values_flat(result)
        if flat is None:
            return None
        node = decoding.node
        if len(flat) != node.point_count:
            raise ValueError(
                "GribJump result size does not match bulk spatial selection: " f"{len(flat)} != {node.point_count}"
            )
        if decoding.sorted_output_positions is None:
            return np.array(flat, dtype=np.float64)
        values = np.empty(node.point_count, dtype=np.float64)
        values[decoding.sorted_output_positions] = flat
        return values

    @classmethod
    def assign_bulk_result(cls, result, decoding):
        """Append one field's values to a bulk node's ``result``, back in the node's point order."""
        values = cls.bulk_field_values(result, decoding)
        if values is None:
            values = np.full(decoding.node.point_count, None, dtype=object)
        decoding.node.result.append(values)

    def datacube_natural_indexes(self, axis, subarray):
        indexes = subarray.get(axis.name, None)
        return indexes

    def select(self, path, unmapped_path):
        return self.fdb_coordinates

    def ax_vals(self, name):
        return self.fdb_coordinates.get(name, None)

    def prep_tree_encoding(self, node, unwanted_path=None):
        # TODO: prepare the tree for protobuf encoding
        # ie transform all axes for gribjump and adding the index property on the leaves
        if unwanted_path is None:
            unwanted_path = {}

        ax = node.axis
        new_node, unwanted_path = ax.unmap_tree_node(node, unwanted_path)

        if len(node.children) != 0:
            for c in new_node.children:
                self.prep_tree_encoding(c, unwanted_path)

    def prep_tree_decoding(self, tree):
        # TODO: transform the tree after decoding from protobuf
        # ie unstransform all axes from gribjump and put the indexes back as a leaf/extra node
        pass
