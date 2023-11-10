from copy import deepcopy

import pyfdb

from .datacube import Datacube, IndexTree


def update_fdb_dataarray(fdb_dataarray):
    fdb_dataarray["values"] = []
    return fdb_dataarray


class FDBDatacube(Datacube):
    def __init__(self, config={}, axis_options={}):
        self.axis_options = axis_options
        self.grid_mapper = None
        self.axis_counter = 0
        self._axes = None
        treated_axes = []
        self.non_complete_axes = []
        self.complete_axes = []
        self.blocked_axes = []
        self.unwanted_axes = []
        self.transformation = None
        self.fake_axes = []
        self.final_path = {"class" : 0, "date": 0, "domain": 0, "expver": 0, "levtype": 0, "param": 0,
                           "step" : 0, "stream": 0, "time": 0, "type": 0, "values": 0}
        self.unwanted_path = {}

        partial_request = config
        # Find values in the level 3 FDB datacube
        # Will be in the form of a dictionary? {axis_name:values_available, ...}
        self.fdb = pyfdb.FDB()
        fdb_dataarray = self.fdb.axes(partial_request).as_dict()
        dataarray = update_fdb_dataarray(fdb_dataarray)
        self.dataarray = dataarray
        for name, values in dataarray.items():
            values.sort()
            options = axis_options.get(name, {})
            self._check_and_add_axes(options, name, values)
            treated_axes.append(name)
            self.complete_axes.append(name)

        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in treated_axes:
                options = axis_options.get(name, {})
                val = self._axes[name].type
                self._check_and_add_axes(options, name, val)

    def remove_unwanted_axes(self, leaf_path):
        for axis in self.unwanted_axes:
            leaf_path.pop(axis)
        return leaf_path

    def get(self, requests: IndexTree, leaf_path={}):
        # First when request node is root, go to its children
        if requests.axis.name == "root":
            if len(requests.children) == 0:
                pass
            else:
                for c in requests.children:
                    self.get(c)

        # Second if request node has no children, we have a leaf so need to assign fdb values to it
        else:
            key_value_path = {requests.axis.name: requests.value}
            ax = requests.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path,
                                                                                  self.unwanted_path)
            leaf_path |= key_value_path
            if len(requests.children[0].children[0].children) == 0:
                # remap this last key
                self.handle_last_before_last_layer(requests, leaf_path)

            # THIRD otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get(c, leaf_path)

    def handle_last_before_last_layer(self, requests, leaf_path={}):
        range_lengths = [[1]*200]*200
        current_start_idxs = [[None]*200]*200
        fdb_node_ranges = [[[IndexTree.root]*200]*200]*200
        lat_length = len(requests.children)
        for i in range(len(requests.children)):
            lat_child = requests.children[i]
            range_length = deepcopy(range_lengths[i])
            current_start_idx = deepcopy(current_start_idxs[i])
            fdb_range_nodes = deepcopy(fdb_node_ranges[i])
            key_value_path = {lat_child.axis.name: lat_child.value}
            ax = lat_child.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path,
                                                                                  self.unwanted_path)
            leaf_path |= key_value_path
            (range_lengths[i],
             current_start_idxs[i],
             fdb_node_ranges[i]) = self.get_last_layer_before_leaf(lat_child, leaf_path, range_length,
                                                                   current_start_idx, fdb_range_nodes)
        self.give_fdb_val_to_node(leaf_path, range_lengths, current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_layer_before_leaf(self, requests, leaf_path, range_l, current_idx, fdb_range_n):
        i = 0
        for c in requests.children:
            # now c are the leaves of the initial tree
            key_value_path = {c.axis.name: c.value}
            ax = c.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path,
                                                                                  self.unwanted_path)
            leaf_path |= key_value_path
            last_idx = key_value_path["values"]
            if current_idx[i] is None:
                current_idx[i] = last_idx
                fdb_range_n[i][range_l[i]-1] = c
            else:
                if last_idx == current_idx[i] + range_l[i]:
                    range_l[i] += 1
                    fdb_range_n[i][range_l[i]-1] = c
                else:
                    key_value_path = {c.axis.name: c.value}
                    ax = c.axis
                    (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path,
                                                                                          self.unwanted_path)
                    leaf_path |= key_value_path
                    i += 1
                    current_start_idx = key_value_path["values"]
                    current_idx[i] = current_start_idx
        return (range_l, current_idx, fdb_range_n)

    def give_fdb_val_to_node(self, leaf_path, range_lengths, current_start_idx, fdb_range_nodes, lat_length):
        (output_values, original_indices) = self.find_fdb_values(leaf_path, range_lengths, current_start_idx,
                                                                 lat_length)
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
                n.result = output_values[0][0][0][i][k]

    def find_fdb_values(self, path, range_lengths, current_start_idx, lat_length):
        path.pop("values")
        fdb_requests = []
        interm_request_ranges = []
        for i in range(lat_length):
            for j in range(200):
                if current_start_idx[i][j] is not None:
                    current_request_ranges = (current_start_idx[i][j], current_start_idx[i][j] + range_lengths[i][j])
                    interm_request_ranges.append(current_request_ranges)
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        sorted_request_ranges = [item[1] for item in sorted_list]
        original_indices = [item[0] for item in sorted_list]
        fdb_requests.append(tuple((path, sorted_request_ranges)))
        subxarray = self.fdb.extract(fdb_requests)
        output_values = subxarray
        return (output_values, original_indices)

    def datacube_natural_indexes(self, axis, subarray):
        indexes = subarray[axis.name]
        return indexes

    def select(self, path, unmapped_path):
        return self.dataarray

    def ax_vals(self, name):
        return self.dataarray.get(name, None)
