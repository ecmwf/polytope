import logging
import operator
import time
from copy import copy, deepcopy
from itertools import product

import numpy as np

from ...utility.exceptions import BadGridError, BadRequestError, GribJumpNoIndexError
from ...utility.geometry import nearest_pt
from ..fdb_assign import FieldRequests, field_values_flat
from ..tensor_index_tree import (
    BulkGridTensorIndexNode,
    BulkMergedTensorIndexNode,
    MergedTensorIndexNode,
)
from ..tree_fold import fold_into_bulk_grid
from ..tree_values import is_array, take, values_hash_key
from .datacube import Datacube, TensorIndexTree


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
        self._leaf_result_orders = {}
        self.axis_options = axis_options
        # When True, the latitude -> longitude layers returned by the hullslicer are folded into a
        # single BulkGridTensorIndexNode per path before retrieval
        self.bulk_grid_leaves = False

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
        * ``leaf_values``: ``[(leaf, values), ...]``, one entry per longitude leaf of the field's sub-tree in tree
          order, ``values`` a fresh float64 array of ``len(leaf.values)`` points (NaN where a point is
          bitmap-missing).  Concatenating them in order gives the field's points in the order ``get`` writes them
          into the leaves.  It is ``None`` when gribjump has no message for the field (what ``get`` records as
          ``None`` values), so that a caller can detect a missing field without reading any value.  When the
          spatial layers are folded into bulk nodes (``bulk_grid_leaves``) the list holds one
          ``(bulk node, values)`` entry per spatial sub-tree, ``values`` in the node's point order.

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
        open_requests = None
        for k, result in enumerate(iterator):
            decoding = decoding_info[k]
            if isinstance(decoding, BulkFDBDecoding):
                values = self.bulk_field_values(result, decoding)
                del result
                yield uncompressed_requests[k][0], None if values is None else [(decoding.node, values)]
                del values
                continue
            field_requests, field_index = decoding
            if field_requests is not open_requests:
                if open_requests is not None:
                    open_requests.release()
                open_requests = field_requests
            flat = field_values_flat(result)
            del result  # drop gribjump's result as soon as its values are readable
            plan = field_requests.plan()
            if flat is None:
                yield uncompressed_requests[k][0], None
            else:
                values = plan.field_arrays(flat)
                del flat
                yield uncompressed_requests[k][0], values
                del values  # let the caller's field go before the next one is read
        if open_requests is not None:
            open_requests.release()

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

        Reorders and de-duplicates the longitude leaf values of ``requests`` in place (see :meth:`prepare`).  The
        decoding info holds one entry per request: either a ``(FieldRequests, field index)`` pair -- the
        ``FieldRequests`` of a spatial sub-tree is shared by all of its fields and knows where each field's values
        belong -- or the :class:`BulkFDBDecoding` of a bulk spatial node, shared by all of its fields.
        """
        # never carry unmapping state over from a previous get
        self.unwanted_path = {}
        # id(leaf) -> positions of its values in grid-index order, for leaves whose values keep their order
        self._leaf_result_orders = {}
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
            decoding = fdb_requests_decoding_info[j]
            if isinstance(decoding, BulkFDBDecoding):
                # one bulk node holds the whole spatial selection; every field decodes the same way
                field_decodings = [decoding] * n_fields
            else:
                original_indices, fdb_node_ranges = decoding
                field_requests = FieldRequests(
                    original_indices,
                    fdb_node_ranges,
                    compressed_request[1],
                    n_fields,
                    self._leaf_result_orders,
                )
                field_decodings = [(field_requests, field_index) for field_index in range(n_fields)]

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
        merged_leaf=False,
    ):
        if leaf_path is None:
            leaf_path = {}

        # First when request node is root, go to its children
        # if isinstance(requests, TensorIndexTree):
        if not merged_leaf:
            if requests.axis.name == "root":
                logging.debug("Looking for data for the tree")

                for c in requests.children:
                    self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info)
            # If request node has no children, we have a leaf so need to assign fdb values to it
            else:
                key_value_path = {requests.axis.name: requests.values}
                ax = requests.axis
                key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(
                    key_value_path, leaf_path, self.unwanted_path
                )
                leaf_path.update(key_value_path)
                # Bulk coupled-axis leaves carry all selected canonical indexes
                # in one array-backed node.
                if isinstance(requests.children[0], BulkMergedTensorIndexNode):
                    for bulk_node in requests.children:
                        path, ranges, decoding = self.get_bulk_merged_values(bulk_node, leaf_path)
                        fdb_requests.append((path, ranges))
                        fdb_requests_decoding_info.append(decoding)
                # Legacy merged lat-lon leaves are represented one point per node.
                elif isinstance(requests.children[0], MergedTensorIndexNode):
                    (
                        path,
                        current_start_idxs,
                        fdb_node_ranges,
                        lat_length,
                    ) = self.get_merged_2nd_last_values(requests, leaf_path)
                    (
                        original_indices,
                        sorted_request_ranges,
                        fdb_node_ranges,
                    ) = self.sort_fdb_request_ranges(current_start_idxs, lat_length, fdb_node_ranges)
                    fdb_requests.append((path, sorted_request_ranges))
                    fdb_requests_decoding_info.append((original_indices, fdb_node_ranges))
                elif isinstance(requests.children[0].children[0], BulkMergedTensorIndexNode):
                    for child in requests.children:
                        self.get_fdb_requests(child, fdb_requests, fdb_requests_decoding_info, leaf_path)
                elif len(requests.children[0].children[0].children) == 0:
                    if self.bulk_grid_leaves and isinstance(requests.children[0].children[0], TensorIndexTree):
                        grid_node = self.fold_into_bulk_grid(requests, leaf_path)
                        if grid_node is not None:
                            path, ranges, decoding = self.get_bulk_merged_values(grid_node, leaf_path)
                            fdb_requests.append((path, ranges))
                            fdb_requests_decoding_info.append(decoding)
                    elif isinstance(requests.children[0].children[0], TensorIndexTree):
                        # find the fdb_requests and associated nodes to which to add results
                        (
                            path,
                            current_start_idxs,
                            fdb_node_ranges,
                            lat_length,
                        ) = self.get_2nd_last_values(requests, leaf_path)
                        (
                            original_indices,
                            sorted_request_ranges,
                            fdb_node_ranges,
                        ) = self.sort_fdb_request_ranges(current_start_idxs, lat_length, fdb_node_ranges)
                        fdb_requests.append((path, sorted_request_ranges))
                        fdb_requests_decoding_info.append((original_indices, fdb_node_ranges))
                    else:
                        merged_leaf = True
                        for c in requests.children:
                            self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info, leaf_path, merged_leaf)

                # Otherwise remap the path for this key and iterate again over children
                else:
                    for c in requests.children:
                        self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info, leaf_path)
        if merged_leaf and len(requests.children[0].children) == 0:
            if isinstance(requests, TensorIndexTree):
                key_value_path = {requests.axis.name: requests.values}
                ax = requests.axis
                key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(
                    key_value_path, leaf_path, self.unwanted_path
                )
                leaf_path.update(key_value_path)

                path, current_start_idxs, fdb_node_ranges, lat_length = self.get_merged_2nd_last_values(
                    requests, leaf_path
                )
                original_indices, sorted_request_ranges, fdb_node_ranges = self.sort_fdb_request_ranges(
                    current_start_idxs, lat_length, fdb_node_ranges
                )
                fdb_requests.append((path, sorted_request_ranges))
                fdb_requests_decoding_info.append((original_indices, fdb_node_ranges))

    def remove_duplicates_in_request_ranges(self, fdb_node_ranges, current_start_idxs):
        # First pass: identify which (i, k) "wins" each index (first occurrence).
        # seen_indices maps idx -> (i, k)
        seen_indices = {}
        # Track which (i,k,j) are duplicates of an earlier node
        is_dup = {}

        for i, idxs_list in enumerate(current_start_idxs):
            for k, sub_lat_idxs in enumerate(idxs_list):
                for j, idx in enumerate(sub_lat_idxs):
                    if idx not in seen_indices:
                        seen_indices[idx] = (i, k)
                    else:
                        is_dup[(i, k, j)] = True

        # Second pass: build new structures
        new_fdb_node_ranges = []
        new_current_start_idxs = []
        nodes_to_remove = []
        nodes_to_update = []  # (node, kept value positions)
        for i, idxs_list in enumerate(current_start_idxs):
            new_idx_group = []
            new_fdb_group = []
            for k, sub_lat_idxs in enumerate(idxs_list):
                actual_fdb_node = fdb_node_ranges[i][k]
                node = actual_fdb_node[0]
                # Collect non-duplicate indices and values for this node
                filtered_idxs = []
                kept_positions = []
                for j, idx in enumerate(sub_lat_idxs):
                    if (i, k, j) not in is_dup:
                        filtered_idxs.append(idx)
                        kept_positions.append(j)
                if filtered_idxs:
                    if len(kept_positions) != len(node.values):
                        nodes_to_update.append((node, kept_positions))
                    new_idx_group.append(filtered_idxs)
                    new_fdb_group.append(actual_fdb_node)
                else:
                    # All indices were duplicates — remove this node from the result tree
                    nodes_to_remove.append(node)
            new_current_start_idxs.append(new_idx_group)
            new_fdb_node_ranges.append(new_fdb_group)

        # Remove empty nodes first (before mutating values, to preserve SortedList ordering)
        for node in nodes_to_remove:
            node.remove_branch()

        # Now safely mutate winner node values (trim any partially-duplicate values)
        for node, kept_positions in nodes_to_update:
            node.values = take(node.values, kept_positions)

        return new_fdb_node_ranges, new_current_start_idxs

    def nearest_lat_lon_search_merged(self, requests):
        if len(self.nearest_search) != 0:
            first_ax_name = requests.children[0].axes[0].name
            second_ax_name = requests.children[0].axes[1].name

            axes_in_nearest_search = [
                first_ax_name not in self.nearest_search.keys(),
                second_ax_name not in self.nearest_search.keys(),
            ]

            if all(not item for item in axes_in_nearest_search):
                raise Exception("nearest point search axes are wrong")

            second_ax = requests.children[0].axes[1]

            nearest_pts_k = self.nearest_search.get((first_ax_name, second_ax_name), None)
            if nearest_pts_k is None:
                nearest_pts_k = self.nearest_search.get((second_ax_name, first_ax_name), None)
                # swap a copy: the stored points must stay as requested for the next get/prepare
                nearest_pts_k = ([[pt[1], pt[0]] for pt in nearest_pts_k[0]], nearest_pts_k[1])

            k = nearest_pts_k[1]
            if k != 1 and not self.grid_transformation.is_irregular:
                print("k nearest neighbour not supported in hullslicer, defaulting to nearest neighbour.")
                k = 1

            transformed_nearest_pts = []
            for point in nearest_pts_k[0]:
                transformed_nearest_pts.append([point[0], second_ax._remap_val_to_axis_range(point[1])])

            found_latlon_pts = []
            # print("AND HERE")
            # print(requests)
            for latlon_child in requests.children:
                # print(latlon_child.values)
                found_latlon_pts.append([[latlon_child.values[0]], [latlon_child.values[1]]])

            # now find the nearest lat lon to the points requested
            nearest_latlons = []
            for pt in transformed_nearest_pts:
                # print("LOOK NOW")
                # print(found_latlon_pts)
                # print(pt)
                nearest_latlon = nearest_pt(found_latlon_pts, pt, k)
                # print(nearest_latlon)
                nearest_latlons.extend(nearest_latlon)

            # need to remove the branches that do not fit
            latlon_children_by_values = {child.values: child for child in requests.children}
            for latlon_child_val, latlon_child in list(latlon_children_by_values.items()):
                if latlon_child.values not in nearest_latlons:
                    latlon_child.remove_branch()

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

    def get_2nd_last_values(self, requests, leaf_path=None):
        if leaf_path is None:
            leaf_path = {}
        # In this function, we recursively loop over the last two layers of the tree and store the indices of the
        # request ranges in those layers
        self.nearest_lat_lon_search(requests)

        lat_length = len(requests.children)
        current_start_idxs = [False] * lat_length
        fdb_node_ranges = [False] * lat_length
        for i in range(len(requests.children)):
            lat_child = requests.children[i]
            lon_length = len(lat_child.children)
            current_start_idxs[i] = [None] * lon_length
            fdb_node_ranges[i] = [[TensorIndexTree.root for y in range(lon_length)] for x in range(lon_length)]
            current_start_idx = deepcopy(current_start_idxs[i])
            fdb_range_nodes = deepcopy(fdb_node_ranges[i])
            key_value_path = {lat_child.axis.name: lat_child.values}
            ax = lat_child.axis
            key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            (
                current_start_idxs[i],
                fdb_node_ranges[i],
            ) = self.get_last_layer_before_leaf(lat_child, leaf_path, current_start_idx, fdb_range_nodes)

        leaf_path_copy = deepcopy(leaf_path)
        leaf_path_copy.pop("values", None)
        leaf_path_copy.pop("index")
        return (leaf_path_copy, current_start_idxs, fdb_node_ranges, lat_length)

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

    def fold_into_bulk_grid(self, requests, leaf_path):
        """Replace the latitude -> longitude children of ``requests`` by one BulkGridTensorIndexNode.

        See :func:`polytope_feature.datacube.tree_fold.fold_into_bulk_grid`: the rows are unmapped to
        their canonical grid indexes one leaf at a time and concatenated with numpy, in the point
        order ``prepare`` gives the tree without the fold.  Points whose index was already seen on an
        earlier row (eg. a box overlapping itself across the longitude seam) are dropped where they
        were first seen, as ``remove_duplicates_in_request_ranges`` does.  Returns None if no point
        is left.
        """
        return fold_into_bulk_grid(self, requests, leaf_path)

    def get_merged_2nd_last_values(self, requests, leaf_path=None):
        if leaf_path is None:
            leaf_path = {}
        # requests is the parent TensorIndexTree node whose direct children are all
        # MergedTensorIndexNodes (each holding values=(lat, lon) and indexes=[flat_idx]).
        # Iterate over all of them so one FDB request covers the entire shared path.
        self.nearest_lat_lon_search_merged(requests)

        lat_length = len(requests.children)
        current_start_idxs = [None] * lat_length
        fdb_node_ranges = [None] * lat_length

        # print("WHAT ABOUT HERE")
        # print(requests)
        # print(requests.children)

        for i, merged_child in enumerate(requests.children):
            # self.nearest_lat_lon_search_merged(requests)
            # self.nearest_lat_lon_search_merged(merged_child)
            lat_ax = merged_child.axes[0]
            lon_ax = merged_child.axes[1]

            # Two-pass unmapping mirroring get_2nd_last_values + get_last_layer_before_leaf:
            # Pass 1 — lat: stash lat value in unwanted_path (no index produced yet)
            kv_lat = {lat_ax.name: merged_child.values[0]}
            kv_lat, leaf_path, self.unwanted_path = lat_ax.unmap_path_key(kv_lat, leaf_path, self.unwanted_path)
            leaf_path.update(kv_lat)

            # Pass 2 — lon: use stashed lat + pre-computed flat index to obtain FDB index
            kv_lon = {lon_ax.name: merged_child.values[1]}
            leaf_path["index"] = merged_child.indexes
            kv_lon, leaf_path, self.unwanted_path = lon_ax.unmap_path_key(kv_lon, leaf_path, self.unwanted_path)
            flat_indices = list(kv_lon["values"])

            # Proxy protects merged_child.values=(lat, lon) from mutation by
            # sort_fdb_request_ranges / remove_duplicates, while sharing .result so
            # that assign_fdb_output_to_nodes writes back onto the real node.
            proxy = copy(merged_child)
            proxy.values = (merged_child.values[1],)  # length == len(flat_indices)
            proxy.remove_branch = merged_child.remove_branch  # delegate tree removal
            proxy._result_owner = merged_child  # assign_fdb_output_to_nodes writes results onto the real node

            current_start_idxs[i] = [flat_indices]
            # current_start_idxs = [[flat_indices]]
            fdb_node_ranges[i] = [[proxy]]
            # fdb_node_ranges = [[[proxy]]]

        leaf_path_copy = deepcopy(leaf_path)
        leaf_path_copy.pop("values", None)
        leaf_path_copy.pop("index")
        return (leaf_path_copy, current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_layer_before_leaf(self, requests, leaf_path, current_idx, fdb_range_n):
        current_idx = [[] for i in range(len(requests.children))]
        fdb_range_n = [[] for i in range(len(requests.children))]
        for i, c in enumerate(requests.children):
            # now c are the leaves of the initial tree
            key_value_path = {c.axis.name: c.values}
            leaf_path["index"] = c.indexes
            ax = c.axis
            key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            # TODO: change this to accommodate non consecutive indexes being compressed too
            current_idx[i].extend(key_value_path["values"])
            fdb_range_n[i].append(c)
        assert len(current_idx) == len(fdb_range_n)
        for i, node in enumerate(fdb_range_n):
            assert len(node[0].values) == len(current_idx[i])
        return (current_idx, fdb_range_n)

    def assign_fdb_output_to_nodes(self, output_iterator, fdb_requests_decoding_info):
        """Write every field of the gribjump output into the leaves of the tree it was requested for.

        Each result is consumed once, as one contiguous ``values_flat`` buffer sliced into the leaves' results by
        the sub-tree's :class:`~polytope_feature.datacube.fdb_assign.ScatterPlan`, so that nothing is kept per
        request range and no field's values outlive their result.  A leaf's result for the whole call is
        pre-allocated (``n_points x n_fields``, float64, NaN-filled) and filled field by field.
        """
        logging.debug("Assigning GribJump output to tree nodes")
        open_requests = None
        returned_range_arrays = 0
        for k, result in enumerate(output_iterator):
            decoding = fdb_requests_decoding_info[k]
            if isinstance(decoding, BulkFDBDecoding):
                self.assign_bulk_result(result, decoding)
                continue
            field_requests, field_index = decoding
            if field_requests is not open_requests:
                # the requests of a sub-tree are consecutive, so only its plan and leaf results are alive
                if open_requests is not None:
                    open_requests.finish_and_release()
                open_requests = field_requests
            plan = field_requests.plan(allocate=True)
            flat = field_values_flat(result)
            del result  # drop gribjump's result as soon as its values are readable
            plan.assign_field(flat, field_index)
            del flat
        if open_requests is not None:
            open_requests.finish_and_release()
        self.prototype_metrics["returned_range_arrays"] = returned_range_arrays
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

    def sort_fdb_request_ranges(self, current_start_idx, lat_length, fdb_node_ranges):
        # print("WHAT DO WE HAVE HERE THROUGH")
        # print(current_start_idx)
        # print(lat_length)
        # print(fdb_node_ranges)
        (
            new_fdb_node_ranges,
            new_current_start_idx,
        ) = self.remove_duplicates_in_request_ranges(fdb_node_ranges, current_start_idx)
        current_start_idx = new_current_start_idx
        fdb_node_ranges = new_fdb_node_ranges
        interm_request_ranges = []
        # TODO: modify the start indexes to have as many arrays as the request ranges
        new_fdb_node_ranges = []
        for i in range(lat_length):
            interm_fdb_nodes = fdb_node_ranges[i]
            old_interm_start_idx = current_start_idx[i]
            for j in range(len(old_interm_start_idx)):
                # TODO: if we sorted the cyclic values in increasing order on the tree too,
                # then we wouldn't have to sort here?
                sorted_list = sorted(enumerate(old_interm_start_idx[j]), key=lambda x: x[1])
                original_indices_idx, interm_start_idx = zip(*sorted_list)
                for interm_fdb_nodes_obj in interm_fdb_nodes[j]:
                    if getattr(interm_fdb_nodes_obj, "_keep_value_order", False):
                        # merged polygon row: keep the values ascending, remember how to reorder the results
                        if original_indices_idx != tuple(range(len(original_indices_idx))):
                            self._leaf_result_orders[id(interm_fdb_nodes_obj)] = original_indices_idx
                    else:
                        interm_fdb_nodes_obj.values = take(interm_fdb_nodes_obj.values, original_indices_idx)
                if abs(interm_start_idx[-1] + 1 - interm_start_idx[0]) <= len(interm_start_idx):
                    current_request_ranges = (
                        interm_start_idx[0],
                        interm_start_idx[-1] + 1,
                    )
                    interm_request_ranges.append(current_request_ranges)
                    new_fdb_node_ranges.append(interm_fdb_nodes[j])
                else:
                    jumps = list(map(operator.sub, interm_start_idx[1:], interm_start_idx[:-1]))
                    last_idx = 0
                    for k, jump in enumerate(jumps):
                        if jump > 1:
                            current_request_ranges = (
                                interm_start_idx[last_idx],
                                interm_start_idx[k] + 1,
                            )
                            new_fdb_node_ranges.append(interm_fdb_nodes[j])
                            last_idx = k + 1
                            interm_request_ranges.append(current_request_ranges)
                        if k == len(interm_start_idx) - 2:
                            current_request_ranges = (
                                interm_start_idx[last_idx],
                                interm_start_idx[-1] + 1,
                            )
                            interm_request_ranges.append(current_request_ranges)
                            new_fdb_node_ranges.append(interm_fdb_nodes[j])
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        original_indices, sorted_request_ranges = zip(*sorted_list)
        return (original_indices, sorted_request_ranges, new_fdb_node_ranges)

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
