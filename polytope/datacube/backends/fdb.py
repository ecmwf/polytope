from copy import deepcopy

import pygribjump as pygj

from ...utility.geometry import nearest_pt
from .datacube import Datacube, IndexTree

import logging
import copy

class FDBDatacube(Datacube):
    def __init__(self, config=None, axis_options=None):
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

        if config is None:
            config = {}

        if axis_options is None:
            axis_options = {}

        partial_request = config
        # Find values in the level 3 FDB datacube

        self.fdb = pygj.GribJump()
        logging.info(f"Partial Request: {partial_request}")
        self.fdb_coordinates = self.fdb.axes(partial_request)
        logging.info(f"Axes from FDB: {self.fdb_coordinates}")
        # for name, values in self.fdb_coordinates.items():
            # logging.info(f"Axis {name} has {values} values")
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

    def get(self, requests: IndexTree, leaf_path={}):


        # First when request node is root, go to its children
        if requests.axis.name == "root":

            self.gj_request_idx = 0
            self.fdb_requests = []
            self.callback = []
            
            for c in requests.children:
                self.get(c)
        # If request node has no children, we have a leaf so need to assign fdb values to it
        else:
            key_value_path = {requests.axis.name: requests.value}
            ax = requests.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            if len(requests.children[0].children[0].children) == 0:
                # remap this last key
                idx, args = self.get_2nd_last_values(self.gj_request_idx, requests, leaf_path)
                self.callback.append(args)
                self.gj_request_idx += 1


            # Otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get(c, leaf_path)


        # Call once at the end
        if requests.axis.name == "root":
            # logging.info("REQUESTS TO FDB:")
            # for f in self.fdb_requests:
            #     logging.info(f)

            logging.info(f"Requesting {len(self.fdb_requests)} requests from FDB")
            data = self.fdb.extract(self.fdb_requests)
            logging.info(f"FDB request complete.")

            # logging.info("DATA FROM FDB:")
            # for d in data:
            #     logging.info(d)

            for i in range(len(self.callback)):
                # logging.debug(f"STEP {self.fdb_requests[i][0]['step']}, PARAM {self.fdb_requests[i][0]['param']}, NUM {self.fdb_requests[i][0]['number']} -> DATA {data[i][0][0]}")
                self.give_fdb_val_to_node_part_2(data, i, *self.callback[i])

    def get_2nd_last_values(self, gj_request_idx, requests, leaf_path={}):
        # In this function, we recursively loop over the last two layers of the tree and store the indices of the
        # request ranges in those layers
        # TODO: here find nearest point first before retrieving etc
        if len(self.nearest_search) != 0:
            first_ax_name = requests.children[0].axis.name
            second_ax_name = requests.children[0].children[0].axis.name
            nearest_pts = [
                [lat_val, lon_val]
                for (lat_val, lon_val) in zip(
                    self.nearest_search[first_ax_name][0], self.nearest_search[second_ax_name][0]
                )
            ]
            # first collect the lat lon points found
            found_latlon_pts = []
            for lat_child in requests.children:
                for lon_child in lat_child.children:
                    found_latlon_pts.append([lat_child.value, lon_child.value])
            # now find the nearest lat lon to the points requested
            nearest_latlons = []
            for pt in nearest_pts:
                nearest_latlon = nearest_pt(found_latlon_pts, pt)
                nearest_latlons.append(nearest_latlon)
            # TODO: now combine with the rest of the function....
            # TODO: need to remove the branches that do not fit
            lat_children_values = [child.value for child in requests.children]
            for i in range(len(lat_children_values)):
                lat_child_val = lat_children_values[i]
                lat_child = [child for child in requests.children if child.value == lat_child_val][0]
                if lat_child.value not in [latlon[0] for latlon in nearest_latlons]:
                    lat_child.remove_branch()
                else:
                    possible_lons = [latlon[1] for latlon in nearest_latlons if latlon[0] == lat_child.value]
                    lon_children_values = [child.value for child in lat_child.children]
                    for j in range(len(lon_children_values)):
                        lon_child_val = lon_children_values[j]
                        lon_child = [child for child in lat_child.children if child.value == lon_child_val][0]
                        if lon_child.value not in possible_lons:
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
            key_value_path = {lat_child.axis.name: lat_child.value}
            ax = lat_child.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            (range_lengths[i], current_start_idxs[i], fdb_node_ranges[i]) = self.get_last_layer_before_leaf(
                lat_child, leaf_path, range_length, current_start_idx, fdb_range_nodes
            )
        return self.give_fdb_val_to_node_part_1(gj_request_idx, leaf_path, range_lengths, current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_layer_before_leaf(self, requests, leaf_path, range_l, current_idx, fdb_range_n):
        i = 0
        for c in requests.children:
            # now c are the leaves of the initial tree
            key_value_path = {c.axis.name: c.value}
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
                    key_value_path = {c.axis.name: c.value}
                    ax = c.axis
                    (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                        key_value_path, leaf_path, self.unwanted_path
                    )
                    leaf_path.update(key_value_path)
                    i += 1
                    current_start_idx = key_value_path["values"]
                    current_idx[i] = current_start_idx
        return (range_l, current_idx, fdb_range_n)

    def give_fdb_val_to_node_part_1(self, gj_request_idx, leaf_path, range_lengths, current_start_idx, fdb_range_nodes, lat_length):
        
        # PART 1
        (output_values, original_indices) = self.find_fdb_values(
            gj_request_idx, leaf_path, range_lengths, current_start_idx, lat_length
        )

        return gj_request_idx, [original_indices, leaf_path, range_lengths, current_start_idx, fdb_range_nodes, lat_length]
    
    def give_fdb_val_to_node_part_2(self, data, gj_request_idx, original_indices, leaf_path, range_lengths, current_start_idx, fdb_range_nodes, lat_length):
        output_values = data[gj_request_idx]

        # PART 2
        new_fdb_range_nodes = []
        new_range_lengths = []
        for j in range(lat_length):
            for i in range(len(range_lengths[j])):
                if current_start_idx[j][i] is not None:
                    new_fdb_range_nodes.append(fdb_range_nodes[j][i])
                    new_range_lengths.append(range_lengths[j][i])
        sorted_fdb_range_nodes = [new_fdb_range_nodes[i] for i in original_indices]
        sorted_range_lengths = [new_range_lengths[i] for i in original_indices]
        for i in range(len(sorted_fdb_range_nodes)):
            for k in range(sorted_range_lengths[i]):
                n = sorted_fdb_range_nodes[i][k]
                n.result = output_values[0][i][0][k]

    def find_fdb_values(self, gj_request_idx, path, range_lengths, current_start_idx, lat_length):
        path.pop("values")
        # fdb_requests = []
        interm_request_ranges = []
        for i in range(lat_length):
            for j in range(len(range_lengths[i])):
                if current_start_idx[i][j] is not None:
                    current_request_ranges = (current_start_idx[i][j], current_start_idx[i][j] + range_lengths[i][j])
                    interm_request_ranges.append(current_request_ranges)
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        original_indices, sorted_request_ranges = zip(*sorted_list)
        # logging.info("Path is {}".format(path))
        self.fdb_requests.append(tuple((copy.deepcopy(path), copy.deepcopy(sorted_request_ranges))))
        assert len(self.fdb_requests) == gj_request_idx + 1
        # logging.info("REQUEST TO FDB")

        # DONT CALL YET
        # output_values = self.fdb.extract(fdb_requests)
        # logging.debug(output_values)
        return (None, original_indices)

    def datacube_natural_indexes(self, axis, subarray):
        indexes = subarray[axis.name]
        return indexes

    def select(self, path, unmapped_path):
        return self.fdb_coordinates

    def ax_vals(self, name):
        return self.fdb_coordinates.get(name, None)
