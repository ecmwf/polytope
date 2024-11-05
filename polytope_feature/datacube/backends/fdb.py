import logging
import operator
from copy import deepcopy
from itertools import product

from ...utility.exceptions import BadRequestError
from ...utility.geometry import nearest_pt
from .datacube import Datacube, TensorIndexTree


class FDBDatacube(Datacube):
    def __init__(
        self, gj, config=None, axis_options=None, compressed_axes_options=[], alternative_axes=[], context=None
    ):
        if config is None:
            config = {}
        if context is None:
            context = {}

        super().__init__(axis_options, compressed_axes_options)

        logging.info("Created an FDB datacube with options: " + str(axis_options))

        self.unwanted_path = {}
        self.axis_options = axis_options

        partial_request = config
        # Find values in the level 3 FDB datacube

        self.gj = gj
        if len(alternative_axes) == 0:
            self.fdb_coordinates = self.gj.axes(partial_request, ctx=context)
            if len(self.fdb_coordinates) == 0:
                raise BadRequestError(partial_request)
        else:
            self.fdb_coordinates = {}
            for axis_config in alternative_axes:
                self.fdb_coordinates[axis_config.axis_name] = axis_config.values

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

        logging.info("Polytope created axes for %s", self._axes.keys())

    def check_branching_axes(self, request):
        polytopes = request.polytopes()
        for polytope in polytopes:
            for ax in polytope._axes:
                if ax == "levtype":
                    (upper, lower, idx) = polytope.extents(ax)
                    if "sfc" in polytope.points[idx]:
                        self.fdb_coordinates.pop("levelist", None)
        self.fdb_coordinates.pop("quantile", None)
        # TODO: When do these not appear??
        self.fdb_coordinates.pop("direction", None)
        self.fdb_coordinates.pop("frequency", None)

        # NOTE: verify that we also remove the axis object for axes we've removed here
        axes_to_remove = set(self.complete_axes) - set(self.fdb_coordinates.keys())

        # Remove the keys from self._axes
        for axis_name in axes_to_remove:
            self._axes.pop(axis_name, None)

    def get(self, requests: TensorIndexTree, context=None):
        if context is None:
            context = {}
        requests.pprint()
        if len(requests.children) == 0:
            return requests
        fdb_requests = []
        fdb_requests_decoding_info = []
        self.get_fdb_requests(requests, fdb_requests, fdb_requests_decoding_info)

        # here, loop through the fdb requests and request from gj and directly add to the nodes
        complete_list_complete_uncompressed_requests = []
        complete_fdb_decoding_info = []
        for j, compressed_request in enumerate(fdb_requests):
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
        logging.debug("The requests we give GribJump are: %s", complete_list_complete_uncompressed_requests)
        output_values = self.gj.extract(complete_list_complete_uncompressed_requests, context)
        logging.debug("GribJump outputs: %s", output_values)
        self.assign_fdb_output_to_nodes(output_values, complete_fdb_decoding_info)

    def get_fdb_requests(
        self,
        requests: TensorIndexTree,
        fdb_requests=[],
        fdb_requests_decoding_info=[],
        leaf_path=None,
    ):
        if leaf_path is None:
            leaf_path = {}

        # First when request node is root, go to its children
        if requests.axis.name == "root":
            logging.debug("Looking for data for the tree: %s", [leaf.flatten() for leaf in requests.leaves])

            for c in requests.children:
                self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info)
        # If request node has no children, we have a leaf so need to assign fdb values to it
        else:
            key_value_path = {requests.axis.name: requests.values}
            ax = requests.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            if len(requests.children[0].children[0].children) == 0:
                # find the fdb_requests and associated nodes to which to add results
                (path, current_start_idxs, fdb_node_ranges, lat_length) = self.get_2nd_last_values(requests, leaf_path)
                (
                    original_indices,
                    sorted_request_ranges,
                    fdb_node_ranges,
                ) = self.sort_fdb_request_ranges(current_start_idxs, lat_length, fdb_node_ranges)
                fdb_requests.append((path, sorted_request_ranges))
                fdb_requests_decoding_info.append((original_indices, fdb_node_ranges))

            # Otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info, leaf_path)

    def remove_duplicates_in_request_ranges(self, fdb_node_ranges, current_start_idxs):
        seen_indices = set()
        for i, idxs_list in enumerate(current_start_idxs):
            for k, sub_lat_idxs in enumerate(idxs_list):
                actual_fdb_node = fdb_node_ranges[i][k]
                original_fdb_node_range_vals = []
                new_current_start_idx = []
                for j, idx in enumerate(sub_lat_idxs):
                    if idx not in seen_indices:
                        # NOTE: need to remove it from the values in the corresponding tree node
                        # NOTE: need to read just the range we give to gj
                        original_fdb_node_range_vals.append(actual_fdb_node[0].values[j])
                        seen_indices.add(idx)
                        new_current_start_idx.append(idx)
                if original_fdb_node_range_vals != []:
                    actual_fdb_node[0].values = tuple(original_fdb_node_range_vals)
                else:
                    # there are no values on this node anymore so can remove it
                    actual_fdb_node[0].remove_branch()
                if len(new_current_start_idx) == 0:
                    current_start_idxs[i].pop(k)
                else:
                    current_start_idxs[i][k] = new_current_start_idx
        return (fdb_node_ranges, current_start_idxs)

    def nearest_lat_lon_search(self, requests):
        if len(self.nearest_search) != 0:
            first_ax_name = requests.children[0].axis.name
            second_ax_name = requests.children[0].children[0].axis.name

            if first_ax_name not in self.nearest_search.keys() or second_ax_name not in self.nearest_search.keys():
                raise Exception("nearest point search axes are wrong")

            second_ax = requests.children[0].children[0].axis

            nearest_pts = [
                [lat_val, second_ax._remap_val_to_axis_range(lon_val)]
                for (lat_val, lon_val) in zip(
                    self.nearest_search[first_ax_name][0], self.nearest_search[second_ax_name][0]
                )
            ]

            found_latlon_pts = []
            for lat_child in requests.children:
                for lon_child in lat_child.children:
                    found_latlon_pts.append([lat_child.values, lon_child.values])

            # now find the nearest lat lon to the points requested
            nearest_latlons = []
            for pt in nearest_pts:
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
            key_value_path = {lat_child.axis.name: lat_child.values}
            ax = lat_child.axis
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
            key_value_path = {c.axis.name: c.values}
            ax = c.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            # TODO: change this to accommodate non consecutive indexes being compressed too
            current_idx[i].extend(key_value_path["values"])
            fdb_range_n[i].append(c)
        return (current_idx, fdb_range_n)

    def assign_fdb_output_to_nodes(self, output_values, fdb_requests_decoding_info):
        for k in range(len(output_values)):
            request_output_values = output_values[k]
            (
                original_indices,
                fdb_node_ranges,
            ) = fdb_requests_decoding_info[k]
            sorted_fdb_range_nodes = [fdb_node_ranges[i] for i in original_indices]
            for i in range(len(sorted_fdb_range_nodes)):
                n = sorted_fdb_range_nodes[i][0]
                if len(request_output_values[0]) == 0:
                    # If we are here, no data was found for this path in the fdb
                    none_array = [None] * len(n.values)
                    n.result.extend(none_array)
                else:
                    interm_request_output_values = request_output_values[0][i][0]
                    n.result.extend(interm_request_output_values)

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
                    interm_fdb_nodes_obj.values = tuple([interm_fdb_nodes_obj.values[k] for k in original_indices_idx])
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
        (new_node, unwanted_path) = ax.unmap_tree_node(node, unwanted_path)

        if len(node.children) != 0:
            for c in new_node.children:
                self.prep_tree_encoding(c, unwanted_path)

    def prep_tree_decoding(self, tree):
        # TODO: transform the tree after decoding from protobuf
        # ie unstransform all axes from gribjump and put the indexes back as a leaf/extra node
        pass
