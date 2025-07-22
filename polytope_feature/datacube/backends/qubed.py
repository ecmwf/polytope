import logging
import operator
from copy import deepcopy
from itertools import product
from ...utility.exceptions import BadGridError, BadRequestError, GribJumpNoIndexError
from ...utility.geometry import nearest_pt
import pygribjump as pygj
from qubed.value_types import QEnum
import numpy as np

from .datacube import Datacube, TensorIndexTree


class QubedDatacube(Datacube):

    def __init__(
        self, q, datacube_axes, config=None, axis_options=None, compressed_axes_options=[], alternative_axes=[], context=None
    ):
        if config is None:
            config = {}
        if axis_options is None:
            axis_options = {}

        self.q = q
        self.datacube_axes = datacube_axes
        # TODO: should the gj object be passed in instead?
        self.gj = pygj.GribJump()
        super().__init__(axis_options, compressed_axes_options)

        # TODO: where do these come from and are they right?
        self.unwanted_path = {}

        self.axis_options = axis_options
        # Find values in the level 3 FDB datacube

        self.fdb_coordinates = {}

        # TODO: we instead now have a list of axes with the actual axes types...
        # TODO: here use the qubed to find all axes names and then get the values from the first val of the qubed and then apply transformations to get the actual right axis type...
        for axis_name in datacube_axes:
            axis = datacube_axes[axis_name]
            self.fdb_coordinates[axis_name] = [axis.type_eg]

        self.fdb_coordinates["values"] = []
        for name, values in self.fdb_coordinates.items():
            options = None
            for opt in self.axis_options:
                if opt.axis_name == name:
                    options = opt

            self._check_and_add_axes(options, name, values)
            self.treated_axes.append(name)
            self.complete_axes.append(name)

        # # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in self.treated_axes:
                options = None
                for opt in self.axis_options:
                    if opt.axis_name == name:
                        options = opt

                val = self._axes[name].type_eg
                self._check_and_add_axes(options, name, val)

        # TODO: actually should separate axis creation with types from the transformations...
        # TODO: we should create all axes here first maybe?
        # TODO: otherwise, we need to somehow get the axis type information/objects when we transform the polytope points into continuous types?
        # TODO: Also, if we don't have the right axis types from the start here, then when we pre-process the polytopes, it will be wrong...

    def add_axes_dynamically(self, qube_node):
        # TODO: here look if the options have changed and we need to modify the transformations
        changed_options = False
        if not len(qube_node.metadata.items()) == 0:
            changed_options = True

        if changed_options:
            if len(qube_node.children) == 0:
                axis_name = "values"
                vals = []
            else:
                axis_name = qube_node.key
                self._axes.pop(axis_name, None)
                vals = list(qube_node.values)

            options = None

            for opt in self.axis_options:
                if opt.axis_name == axis_name:
                    options = opt

            # NOTE: be sure to remove the "fake" additional grid axes
            if len(qube_node.children) == 0:
                axes_names = list(self._axes.keys())

                for name in axes_names:
                    if name not in self.treated_axes:
                        self._axes.pop(name, None)

            self._check_and_readd_axes(options, axis_name, vals)

            # NOTE: now if we have created the additional grid axes, readd the additional transformations associated to them
            new_axes_names = list(self._axes.keys())
            for name in new_axes_names:
                if name not in self.treated_axes:
                    options = None
                    for opt in self.axis_options:
                        if opt.axis_name == name:
                            options = opt

                    val = [self._axes[name].type_eg]
                    self._check_and_readd_axes(options, name, val)

        # TODO: will this work?? How do we make sure we add the grid axes which come from the values transformation here??
        # TODO: we can't do a "difference" of axes like before since we don't a priori have the final axes set available at once??
        pass

    def datacube_natural_indexes(self, qube_node):
        if qube_node is not None:
            return np.asarray(list(qube_node.values))
        else:
            return []

    def get_indices(self, path, path_node, axis, lower, upper, method=None):
        """
        Given a path to a subset of the datacube, return the discrete indexes which exist between
        two non-discrete values (lower, upper) for a particular axis (given by label)
        If lower and upper are equal, returns the index which exactly matches that value (if it exists)
        e.g. returns integer discrete points between two floats
        """
        indexes = axis.find_indexes_node(path_node, self, path)

        idx_between = axis.find_indices_between(indexes, lower, upper, self, method)

        logging.debug(f"For axis {axis.name} between {lower} and {upper}, found indices {idx_between}")

        return idx_between

    def get(self, requests, context=None):
        if context is None:
            context = {}
        if len(requests.children) == 0:
            return requests
        fdb_requests = []
        fdb_requests_decoding_info = []
        self.get_fdb_requests(requests, fdb_requests, fdb_requests_decoding_info)

        # here, loop through the fdb requests and request from gj and directly add to the nodes
        complete_list_complete_uncompressed_requests = []
        complete_fdb_decoding_info = []
        for j, compressed_request in enumerate(fdb_requests):

            compressed_metadata = compressed_request[2]

            # TODO: get uncompressed metadata for each leaf
            uncompressed_request = {}

            # Need to determine the possible decompressed requests

            # find the possible combinations of compressed indices
            interm_branch_tuple_values = []
            for key in compressed_request[0].keys():
                interm_branch_tuple_values.append(compressed_request[0][key])
            request_combis = product(*interm_branch_tuple_values)

            # Need to extract the possible requests and add them to the right nodes
            for combi in request_combis:
                uncompressed_request = {}
                for i, key in enumerate(compressed_request[0].keys()):
                    uncompressed_request[key] = combi[i]
                complete_uncompressed_request = (uncompressed_request, compressed_request[1], self.grid_md5_hash)
                complete_list_complete_uncompressed_requests.append(complete_uncompressed_request)
                complete_fdb_decoding_info.append(fdb_requests_decoding_info[j])

        if logging.root.level <= logging.DEBUG:
            printed_list_to_gj = complete_list_complete_uncompressed_requests[::1000]
            logging.debug("The requests we give GribJump are: %s", printed_list_to_gj)
        logging.info("Requests given to GribJump extract for %s", context)
        try:
            output_values = self.gj.extract(complete_list_complete_uncompressed_requests, context)
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
        if logging.root.level <= logging.DEBUG:
            printed_output_values = output_values[::1000]
            logging.debug("GribJump outputs: %s", printed_output_values)
        self.assign_fdb_output_to_nodes(output_values, complete_fdb_decoding_info)

    def get_fdb_requests(
        self,
        requests,
        fdb_requests=[],
        fdb_requests_decoding_info=[],
        leaf_path=None,
        leaf_metadata=None,
    ):
        # TODO: collect leaf metadata from qube here too
        if leaf_path is None:
            leaf_path = {}

        if leaf_metadata is None:
            leaf_metadata = {}

        # First when request node is root, go to its children
        if requests.key == "root":
            logging.debug("Looking for data for the tree")

            for c in requests.children:
                self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info)
        # If request node has no children, we have a leaf so need to assign fdb values to it
        else:
            key_value_path = {requests.key: requests.values}
            ax = self._axes[requests.key]
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            # TODO: change to use the datacube trasnformations instead...
            if requests.key == "time":
                new_vals = []
                for val in key_value_path[requests.key]:
                    new_vals.append(val[7:9]+val[10:12])
                key_value_path[requests.key] = new_vals
            if requests.key == "date":
                new_vals = []
                for val in key_value_path[requests.key]:
                    new_vals.append(val[:4] + val[5:7] + val[8:10])
                key_value_path[requests.key] = new_vals
            leaf_path.update(key_value_path)
            leaf_metadata.update(requests.metadata)
            if len(requests.children[0].children[0].children) == 0:
                # find the fdb_requests and associated nodes to which to add results
                (path, current_start_idxs, fdb_node_ranges, lat_length) = self.get_2nd_last_values(requests, leaf_path)
                (
                    original_indices,
                    sorted_request_ranges,
                    fdb_node_ranges,
                ) = self.sort_fdb_request_ranges(current_start_idxs, lat_length, fdb_node_ranges)
                fdb_requests.append((path, sorted_request_ranges, leaf_metadata))
                fdb_requests_decoding_info.append((original_indices, fdb_node_ranges))

            # Otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info, leaf_path, leaf_metadata)

    def remove_duplicates_in_request_ranges(self, fdb_node_ranges, current_start_idxs):
        # seen_indices = set()
        # for i, idxs_list in enumerate(current_start_idxs):
        #     for k, sub_lat_idxs in enumerate(idxs_list):
        #         actual_fdb_node = fdb_node_ranges[i][k]
        #         original_fdb_node_range_vals = []
        #         new_current_start_idx = []
        #         for j, idx in enumerate(sub_lat_idxs):
        #             if idx not in seen_indices:
        #                 # NOTE: need to remove it from the values in the corresponding tree node
        #                 # NOTE: need to read just the range we give to gj
        #                 original_fdb_node_range_vals.append(list(actual_fdb_node[0].values)[j])
        #                 seen_indices.add(idx)
        #                 new_current_start_idx.append(idx)
        #         if original_fdb_node_range_vals != []:
        #             actual_fdb_node[0].values = tuple(original_fdb_node_range_vals)
        #         else:
        #             # there are no values on this node anymore so can remove it
        #             actual_fdb_node[0].remove_branch()
        #         if len(new_current_start_idx) == 0:
        #             current_start_idxs[i].pop(k)
        #         else:
        #             current_start_idxs[i][k] = new_current_start_idx
        return (fdb_node_ranges, current_start_idxs)

    def nearest_lat_lon_search(self, requests):
        if len(self.nearest_search) != 0:
            first_ax_name = requests.children[0].key
            second_ax_name = requests.children[0].children[0].key

            axes_in_nearest_search = [
                first_ax_name not in self.nearest_search.keys(),
                second_ax_name not in self.nearest_search.keys(),
            ]

            if all(not item for item in axes_in_nearest_search):
                raise Exception("nearest point search axes are wrong")

            second_ax = self._axes[requests.children[0].children[0].key]

            nearest_pts = self.nearest_search.get((first_ax_name, second_ax_name), None)
            if nearest_pts is None:
                nearest_pts = self.nearest_search.get((second_ax_name, first_ax_name), None)
                for i, pt in enumerate(nearest_pts):
                    nearest_pts[i] = [pt[1], pt[0]]

            transformed_nearest_pts = []
            for point in nearest_pts:
                transformed_nearest_pts.append([point[0], second_ax._remap_val_to_axis_range(point[1])])

            found_latlon_pts = []
            for lat_child in requests.children:
                for lon_child in lat_child.children:
                    found_latlon_pts.append([lat_child.values, lon_child.values])

            # now find the nearest lat lon to the points requested
            nearest_latlons = []
            for pt in transformed_nearest_pts:
                nearest_latlon = nearest_pt(found_latlon_pts, pt)
                nearest_latlons.append(nearest_latlon)

            # need to remove the branches that do not fit
            lat_children_values = [child.values for child in requests.children]
            for i in range(len(lat_children_values)):
                lat_child_val = lat_children_values[i]
                lat_child = [child for child in requests.children if child.values == lat_child_val][0]
                if lat_child.values not in [(latlon[0],) for latlon in nearest_latlons]:
                    lat_child.remove_branch()
                else:
                    possible_lons = [latlon[1] for latlon in nearest_latlons if (latlon[0],) == lat_child.values]
                    lon_children_values = [child.values for child in lat_child.children]
                    for j in range(len(lon_children_values)):
                        lon_child_val = lon_children_values[j]
                        lon_child = [child for child in lat_child.children if child.values == lon_child_val][0]
                        for value in lon_child.values:
                            if value not in possible_lons:
                                lon_child.remove_compressed_branch(value)

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
            key_value_path = {lat_child.key: list(lat_child.values)}
            # print("WHAT ARE THE DATACUBE AXES NOW??")
            # print(self._axes.keys())
            ax = self._axes[lat_child.key]
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            (current_start_idxs[i], fdb_node_ranges[i]) = self.get_last_layer_before_leaf(
                lat_child, leaf_path, current_start_idx, fdb_range_nodes
            )

        leaf_path_copy = deepcopy(leaf_path)
        leaf_path_copy.pop("values", None)
        return (leaf_path_copy, current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_layer_before_leaf(self, requests, leaf_path, current_idx, fdb_range_n):
        current_idx = [[] for i in range(len(requests.children))]
        fdb_range_n = [[] for i in range(len(requests.children))]
        for i, c in enumerate(requests.children):
            # now c are the leaves of the initial tree
            key_value_path = {c.key: list(c.values)}
            ax = self._axes[c.key]
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            # TODO: change this to accommodate non consecutive indexes being compressed too
            current_idx[i].extend(key_value_path["values"])
            fdb_range_n[i].append(c)
        return (current_idx, fdb_range_n)

    def assign_fdb_output_to_nodes(self, output_values, fdb_requests_decoding_info):
        for k, request_output_values in enumerate(output_values):
            (
                original_indices,
                fdb_node_ranges,
            ) = fdb_requests_decoding_info[k]
            sorted_fdb_range_nodes = [fdb_node_ranges[i] for i in original_indices]
            for i in range(len(sorted_fdb_range_nodes)):
                n = sorted_fdb_range_nodes[i][0]
                if len(request_output_values.values) == 0:
                    # If we are here, no data was found for this path in the fdb
                    none_array = [None] * len(n.values)
                    if n.data.metadata.get("result", None) is None:
                        n.data.metadata["result"] = []
                    n.data.metadata["result"].extend(none_array)
                else:
                    if n.data.metadata.get("result", None) is None:
                        n.data.metadata["result"] = []
                    n.data.metadata["result"].extend(request_output_values.values[i])

    def sort_fdb_request_ranges(self, current_start_idx, lat_length, fdb_node_ranges):
        (new_fdb_node_ranges, new_current_start_idx) = self.remove_duplicates_in_request_ranges(
            fdb_node_ranges, current_start_idx
        )
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
                    interm_fdb_nodes_obj.data.values = QEnum(tuple([list(interm_fdb_nodes_obj.values)[k]
                                                                    for k in original_indices_idx]))
                if abs(interm_start_idx[-1] + 1 - interm_start_idx[0]) <= len(interm_start_idx):
                    current_request_ranges = (interm_start_idx[0], interm_start_idx[-1] + 1)
                    interm_request_ranges.append(current_request_ranges)
                    new_fdb_node_ranges.append(interm_fdb_nodes[j])
                else:
                    jumps = list(map(operator.sub, interm_start_idx[1:], interm_start_idx[:-1]))
                    last_idx = 0
                    for k, jump in enumerate(jumps):
                        if jump > 1:
                            current_request_ranges = (interm_start_idx[last_idx], interm_start_idx[k] + 1)
                            new_fdb_node_ranges.append(interm_fdb_nodes[j])
                            last_idx = k + 1
                            interm_request_ranges.append(current_request_ranges)
                        if k == len(interm_start_idx) - 2:
                            current_request_ranges = (interm_start_idx[last_idx], interm_start_idx[-1] + 1)
                            interm_request_ranges.append(current_request_ranges)
                            new_fdb_node_ranges.append(interm_fdb_nodes[j])
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        original_indices, sorted_request_ranges = zip(*sorted_list)
        return (original_indices, sorted_request_ranges, new_fdb_node_ranges)
