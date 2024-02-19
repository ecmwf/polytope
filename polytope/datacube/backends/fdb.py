import logging
from copy import deepcopy

import pygribjump as pygj

from ...utility.geometry import nearest_pt
from .datacube import Datacube, IndexTree


class FDBDatacube(Datacube):
    def __init__(self, config=None, axis_options=None, datacube_options=None):
        if config is None:
            config = {}
        if axis_options is None:
            axis_options = {}
        if datacube_options is None:
            datacube_options = {}

        logging.info("Created an FDB datacube with options: " + str(axis_options))

        self.axis_options = axis_options
        self.axis_counter = 0
        self._axes = None
        treated_axes = []
        self.complete_axes = []
        self.blocked_axes = []
        self.fake_axes = []
        self.unwanted_path = {}
        self.nearest_search = {}
        self.coupled_axes = []
        self.axis_with_identical_structure_after = datacube_options.get("identical structure after")

        partial_request = config
        # Find values in the level 3 FDB datacube

        self.gj = pygj.GribJump()
        self.fdb_coordinates = self.gj.axes(partial_request)

        logging.info("Axes returned from GribJump are: " + str(self.fdb_coordinates))

        self.fdb_coordinates["values"] = []
        for name, values in self.fdb_coordinates.items():
            values.sort()
            options = axis_options.get(name, None)
            self._check_and_add_axes(options, name, values)
            treated_axes.append(name)
            self.complete_axes.append(name)

        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in treated_axes:
                options = axis_options.get(name, None)
                val = self._axes[name].type
                self._check_and_add_axes(options, name, val)

        logging.info("Polytope created axes for: " + str(self._axes.keys()))

    def get(self, requests: IndexTree):
        fdb_requests = []
        fdb_requests_decoding_info = []
        self.get_fdb_requests(requests, fdb_requests, fdb_requests_decoding_info)
        for request in fdb_requests:
            for key in request[0].keys():
                # remove the tuple of the request when we ask the fdb
                request[0][key] = request[0][key][0]
        output_values = self.gj.extract(fdb_requests)
        self.assign_fdb_output_to_nodes(output_values, fdb_requests_decoding_info)

    def get_fdb_requests(self, requests: IndexTree, fdb_requests=[], fdb_requests_decoding_info=[], leaf_path=None):
        if leaf_path is None:
            leaf_path = {}

        # First when request node is root, go to its children
        if requests.axis.name == "root":
            logging.info("Looking for data for the tree: " + str([leaf.flatten() for leaf in requests.leaves]))

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

                (path, range_lengths, current_start_idxs, fdb_node_ranges, lat_length) = self.get_2nd_last_values(
                    requests, leaf_path
                )
                (original_indices, sorted_request_ranges) = self.sort_fdb_request_ranges(
                    range_lengths, current_start_idxs, lat_length
                )
                fdb_requests.append(tuple((path, sorted_request_ranges)))
                fdb_requests_decoding_info.append(
                    tuple((original_indices, fdb_node_ranges, lat_length, range_lengths, current_start_idxs))
                )

            # Otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get_fdb_requests(c, fdb_requests, fdb_requests_decoding_info, leaf_path)

    def get_2nd_last_values(self, requests, leaf_path=None):
        if leaf_path is None:
            leaf_path = {}
        # In this function, we recursively loop over the last two layers of the tree and store the indices of the
        # request ranges in those layers

        # Find nearest point first before retrieving
        if len(self.nearest_search) != 0:
            first_ax_name = requests.children[0].axis.name
            second_ax_name = requests.children[0].children[0].axis.name
            # TODO: throw error if first_ax_name or second_ax_name not in self.nearest_search.keys()
            second_ax = requests.children[0].children[0].axis

            # TODO: actually, here we should not remap the nearest_pts, we should instead unmap the
            # found_latlon_pts and then remap them later once we have compared found_latlon_pts and nearest_pts
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
                    possible_lons = [(latlon[1],) for latlon in nearest_latlons if (latlon[0],) == lat_child.values]
                    lon_children_values = [child.values for child in lat_child.children]
                    for j in range(len(lon_children_values)):
                        lon_child_val = lon_children_values[j]
                        lon_child = [child for child in lat_child.children if child.values == lon_child_val][0]
                        if lon_child.values not in possible_lons:
                            lon_child.remove_branch()

        lat_length = len(requests.children)
        range_lengths = [False] * lat_length
        current_start_idxs = [False] * lat_length
        fdb_node_ranges = [False] * lat_length
        for i in range(len(requests.children)):
            lat_child = requests.children[i]
            lon_length = len(lat_child.children)
            range_lengths[i] = [1] * lon_length
            current_start_idxs[i] = [None] * lon_length
            fdb_node_ranges[i] = [[IndexTree.root] * lon_length] * lon_length
            range_length = deepcopy(range_lengths[i])
            current_start_idx = deepcopy(current_start_idxs[i])
            fdb_range_nodes = deepcopy(fdb_node_ranges[i])
            key_value_path = {lat_child.axis.name: lat_child.values}
            ax = lat_child.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            (range_lengths[i], current_start_idxs[i], fdb_node_ranges[i]) = self.get_last_layer_before_leaf(
                lat_child, leaf_path, range_length, current_start_idx, fdb_range_nodes
            )

        leaf_path_copy = deepcopy(leaf_path)
        leaf_path_copy.pop("values", None)
        return (leaf_path_copy, range_lengths, current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_layer_before_leaf(self, requests, leaf_path, range_l, current_idx, fdb_range_n):
        i = 0
        for c in requests.children:
            # now c are the leaves of the initial tree
            key_value_path = {c.axis.name: c.values}
            ax = c.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            last_idx = key_value_path["values"]
            if current_idx[i] is None:
                current_idx[i] = last_idx
                fdb_range_n[i][range_l[i] - 1] = c
            else:
                if last_idx == current_idx[i] + range_l[i]:
                    range_l[i] += 1
                    fdb_range_n[i][range_l[i] - 1] = c
                else:
                    key_value_path = {c.axis.name: c.values}
                    ax = c.axis
                    (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                        key_value_path, leaf_path, self.unwanted_path
                    )
                    leaf_path.update(key_value_path)
                    i += 1
                    current_start_idx = key_value_path["values"]
                    current_idx[i] = current_start_idx
        return (range_l, current_idx, fdb_range_n)

    def assign_fdb_output_to_nodes(self, output_values, fdb_requests_decoding_info):
        for k in range(len(output_values)):
            request_output_values = output_values[k]
            (
                original_indices,
                fdb_node_ranges,
                lat_length,
                range_lengths,
                current_start_idxs,
            ) = fdb_requests_decoding_info[k]
            new_fdb_range_nodes = []
            new_range_lengths = []
            for j in range(lat_length):
                for i in range(len(range_lengths[j])):
                    if current_start_idxs[j][i] is not None:
                        new_fdb_range_nodes.append(fdb_node_ranges[j][i])
                        new_range_lengths.append(range_lengths[j][i])
            sorted_fdb_range_nodes = [new_fdb_range_nodes[i] for i in original_indices]
            sorted_range_lengths = [new_range_lengths[i] for i in original_indices]
            for i in range(len(sorted_fdb_range_nodes)):
                for j in range(sorted_range_lengths[i]):
                    n = sorted_fdb_range_nodes[i][j]
                    n.result = request_output_values[0][i][0][j]

    def sort_fdb_request_ranges(self, range_lengths, current_start_idx, lat_length):
        interm_request_ranges = []
        for i in range(lat_length):
            for j in range(len(range_lengths[i])):
                if current_start_idx[i][j] is not None:
                    current_request_ranges = (current_start_idx[i][j], current_start_idx[i][j] + range_lengths[i][j])
                    interm_request_ranges.append(current_request_ranges)
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        original_indices, sorted_request_ranges = zip(*sorted_list)
        return (original_indices, sorted_request_ranges)

    def datacube_natural_indexes(self, axis, subarray):
        indexes = subarray[axis.name]
        return indexes

    def select(self, path, unmapped_path):
        return self.fdb_coordinates

    def ax_vals(self, name):
        return self.fdb_coordinates.get(name, None)
