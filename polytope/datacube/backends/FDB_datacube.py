import math
import time
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
        self.time_fdb = 0
        self.time_unmap_key = 0
        self.other_time = 0
        self.final_path = {"class" : 0, "date": 0, "domain": 0, "expver": 0, "levtype": 0, "param": 0,
                           "step" : 0, "stream": 0, "time": 0, "type": 0, "values": 0}
        # self.unwanted_path = {"latitude": 0}
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

    def get_old(self, requests: IndexTree):
        # NOTE: this will do all the transformation unmappings for all the points
        # It doesn't use the tree structure of the result to do the unmapping transformations anymore
        time_changing_path = 0
        accumulated_fdb_time = 0
        time_change_path = 0
        time_is_nan = 0
        interm_time = 0
        time0 = time.time()
        for r in requests.leaves_with_ancestors:
            time5 = time.time()
            # NOTE: Accumulated time in flatten is 0.14s... could be better?
            path = r.flatten_with_ancestors()
            # path = r.flatten()
            time_change_path += time.time() - time5
            # path = self.remap_path(path)
            if len(path.items()) == self.axis_counter:
                # first, find the grid mapper transform

                unmapped_path = {}
                path_copy = deepcopy(path)
                time2 = time.time()
                for key in path_copy:
                    axis = self._axes[key]
                    (path, unmapped_path) = axis.unmap_total_path_to_datacube(path, unmapped_path)
                time_changing_path += time.time() - time2
                time8 = time.time()
                path = self.fit_path(path)
                # merge path and unmapped path into a single path
                path.update(unmapped_path)

                # fit request into something for pyfdb
                fdb_request_val = path["values"]
                path.pop("values")
                fdb_request_key = path

                fdb_requests = [(fdb_request_key, [(fdb_request_val, fdb_request_val + 1)])]
                interm_time += time.time() - time8
                # need to request data from the fdb
                time1 = time.time()
                subxarray = self.fdb.extract(fdb_requests)
                accumulated_fdb_time += time.time() - time1
                subxarray_output_tuple = subxarray[0][0]
                output_value = subxarray_output_tuple[0][0][0]
                time7 = time.time()
                if not math.isnan(output_value):
                    r.result = output_value
                time_is_nan += time.time() - time7
            else:
                r.remove_branch()
        print("FDB TIME")
        print(accumulated_fdb_time)
        print("GET TIME")
        print(time.time() - time0)
        print("TIME FLATTEN PATH AND CHANGE PATH")
        print(time_change_path)
        print("TIME CHANGING PATH")
        print(time_changing_path)
        print("TIME IS NAN")
        print(time_is_nan)
        print("INTERM TIME")
        print(interm_time)

    def remove_unwanted_axes(self, leaf_path):
        for axis in self.unwanted_axes:
            leaf_path.pop(axis)
        return leaf_path

    def older_get(self, requests: IndexTree, leaf_path={}):
        # First when request node is root, go to its children
        if requests.axis.name == "root":
            if len(requests.children) == 0:
                pass
            else:
                for c in requests.children:
                    self.get(c)

        # Second if request node has no children, we have a leaf so need to assign fdb values to it
        else:
            # time2 = time.time()
            key_value_path = {requests.axis.name: requests.value}
            # self.other_time += time.time() - time2
            ax = requests.axis
            time1 = time.time()
            # (key_value_path, leaf_path) = ax.unmap_path_key(key_value_path, leaf_path)
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
            self.time_unmap_key += time.time() - time1
            time2 = time.time()
            leaf_path |= key_value_path
            self.other_time += time.time() - time2
            if len(requests.children) == 0:
                # remap this last key
                output_value = self.find_fdb_values(leaf_path)
                if not math.isnan(output_value):
                    requests.result = output_value

            # THIRD otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get(c, leaf_path)

    def lon_get(self, requests: IndexTree, leaf_path={}):
        # First when request node is root, go to its children
        if requests.axis.name == "root":
            if len(requests.children) == 0:
                pass
            else:
                for c in requests.children:
                    self.get(c)

        # Second if request node has no children, we have a leaf so need to assign fdb values to it
        else:
            # time2 = time.time()
            key_value_path = {requests.axis.name: requests.value}
            # self.other_time += time.time() - time2
            ax = requests.axis
            time1 = time.time()
            # (key_value_path, leaf_path) = ax.unmap_path_key(key_value_path, leaf_path)
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
            self.time_unmap_key += time.time() - time1
            time2 = time.time()
            leaf_path |= key_value_path
            self.other_time += time.time() - time2
            if len(requests.children[0].children) == 0:
                # remap this last key
                self.get_last_layer_before_leaf(requests, leaf_path)

            # THIRD otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get(c, leaf_path)

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
            # time2 = time.time()
            key_value_path = {requests.axis.name: requests.value}
            # self.other_time += time.time() - time2
            ax = requests.axis
            time1 = time.time()
            # (key_value_path, leaf_path) = ax.unmap_path_key(key_value_path, leaf_path)
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
            self.time_unmap_key += time.time() - time1
            time2 = time.time()
            leaf_path |= key_value_path
            self.other_time += time.time() - time2
            if len(requests.children[0].children[0].children) == 0:
                # remap this last key
                self.handle_last_before_last_layer(requests, leaf_path)

            # THIRD otherwise remap the path for this key and iterate again over children
            else:
                for c in requests.children:
                    self.get(c, leaf_path)

    # def get_last_layer_before_leaf(self, requests, leaf_path={}):
    #     range_length = 1
    #     current_start_idx = None
    #     fdb_range_nodes = [IndexTree.root] * 200
    #     for c in requests.children:
    #         # now c are the leaves of the initial tree
    #         key_value_path = {c.axis.name: c.value}
    #         print(key_value_path)
    #         ax = c.axis
    #         (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
    #         leaf_path |= key_value_path
    #         last_idx = key_value_path["values"]
    #         if current_start_idx is None:
    #             current_start_idx = last_idx
    #         else:
    #             if last_idx == current_start_idx + 1:
    #                 range_length += 1
    #                 fdb_range_nodes[range_length-1] = c
    #             else:
    #                 # here, we jump to another range, so we first extract the old values from the fdb, and then we reset range_length etc...
    #                 self.give_fdb_val_to_node(leaf_path, range_length, current_start_idx, fdb_range_nodes)
    #                 key_value_path = {c.axis.name: c.value}
    #                 ax = c.axis
    #                 (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
    #                 leaf_path |= key_value_path
    #                 current_start_idx = key_value_path["values"]
    #                 range_length = 1
    #                 fdb_range_nodes = [c] * 200
    #     # need to extract the last ranges
    #     self.give_fdb_val_to_node(leaf_path, range_length, current_start_idx, fdb_range_nodes)

    def handle_last_before_last_layer(self, requests, leaf_path={}):
        range_lengths = [[1]*200]*200
        current_start_idxs = [[None]*200]*200
        fdb_node_ranges = [[[IndexTree.root]*200]*200]*200
        lat_length = len(requests.children)
        # requests.pprint()
        for i in range(len(requests.children)):
            lat_child = requests.children[i]
            range_length = deepcopy(range_lengths[i])
            current_start_idx = deepcopy(current_start_idxs[i])
            fdb_range_nodes = deepcopy(fdb_node_ranges[i])
            key_value_path = {lat_child.axis.name: lat_child.value}
            # print(key_value_path)
            ax = lat_child.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
            leaf_path |= key_value_path
            # leaf_path.pop("values", None)
            (range_lengths[i],
             current_start_idxs[i],
             fdb_node_ranges[i]) = self.get_last_last_layer_before_leaf(lat_child,
                                                                        leaf_path,
                                                                        range_length,
                                                                        current_start_idx,
                                                                        fdb_range_nodes)
            # print(current_start_idxs[i])
            # print(lat_length)
            # TODO: now call get_last_last_layer_before_layer on lat_child and add the range_lengths etc to the big array
        # TODO: fetch data from fdb using big arrays
        self.new_give_fdb_val_to_node(leaf_path, range_lengths, current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_last_layer_before_leaf(self, requests, leaf_path, range_l, current_idx, fdb_range_n):
        i = 0
        # range_length = range_l[i]
        # current_start_idx = current_idx[i]
        # fdb_range_nodes = fdb_range_n[i]
        # TODO: need to build the range_lengths etc ranges...
        for c in requests.children:
            # now c are the leaves of the initial tree
            key_value_path = {c.axis.name: c.value}
            # print(key_value_path)
            # print(key_value_path)
            ax = c.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
            # print(key_value_path)
            # print(current_idx[i])
            leaf_path |= key_value_path
            # print("INSIDE SECOND FUNCTION")
            # print(leaf_path)
            last_idx = key_value_path["values"]
            if current_idx[i] is None:
                current_idx[i] = last_idx
                fdb_range_n[i][range_l[i]-1] = c
            else:
                # if last_idx == current_start_idx + 1:
                # print((last_idx, current_start_idx+range_length))
                if last_idx == current_idx[i] + range_l[i]:
                    range_l[i] += 1
                    fdb_range_n[i][range_l[i]-1] = c
                else:
                    # print(key_value_path)
                    # print(last_idx)
                    # print(current_idx[i] + range_l[i])
                    # here, we jump to another range, so we first extract the old values from the fdb, and then we reset range_length etc...
                    # print(range_length)
                    # print(current_start_idx)
                    # self.give_fdb_val_to_node(leaf_path, range_l[i], current_idx[i], fdb_range_n[i])
                    key_value_path = {c.axis.name: c.value}
                    ax = c.axis
                    (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
                    leaf_path |= key_value_path
                    i += 1
                    current_start_idx = key_value_path["values"]
                    current_idx[i] = current_start_idx
                    # range_length = 1
                    # fdb_range_nodes = [IndexTree.root] * 200
        # need to extract the last ranges
        # print(range_l)
        # print(current_idx)
        return (range_l, current_idx, fdb_range_n)
        # self.give_fdb_val_to_node(leaf_path, range_length, current_start_idx, fdb_range_nodes)

    def give_fdb_val_to_node(self, leaf_path, range_length, current_start_idx, fdb_range_nodes):
        output_values = self.new_find_fdb_values(leaf_path, range_length, current_start_idx)
        for i in range(len(fdb_range_nodes[:range_length])):
            n = fdb_range_nodes[i]
            n.result = output_values[i]

    # def get_last_layer_before_leaf(self, requests, leaf_path={}):
    #     range_lengths = [[1]*200]*200
    #     current_start_idx = [[None]*200]*200
    #     fdb_range_nodes = [[[IndexTree.root] * 200]*200]*200
    #     requests_length = len(requests.children)
    #     j=0
    #     # for c in requests.children:
    #     for i in range(len(requests.children)):
    #         c = requests.children[i]
    #         # now c are the leaves of the initial tree
    #         key_value_path = {c.axis.name: c.value}
    #         ax = c.axis
    #         (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
    #         leaf_path |= key_value_path
    #         last_idx = key_value_path["values"]
    #         # print(last_idx)
    #         if current_start_idx[i][j] is None:
    #             current_start_idx[i][j] = last_idx
    #             # print("HERE")
    #         else:
    #             if last_idx == current_start_idx[i][j] + 1:
    #                 range_lengths[i][j] += 1
    #                 fdb_range_nodes[i][j][range_lengths[i][j]-1] = c
    #             else:
    #                 # here, we jump to another range, so we first extract the old values from the fdb, and then we reset range_length etc...
    #                 # self.give_fdb_val_to_node(leaf_path, range_lengths, current_start_idx, fdb_range_nodes, requests_length)
    #                 key_value_path = {c.axis.name: c.value}
    #                 ax = c.axis
    #                 (key_value_path, leaf_path, self.unwanted_path) = ax.n_unmap_path_key(key_value_path, leaf_path, self.unwanted_path)
    #                 j += 1
    #                 leaf_path |= key_value_path
    #                 current_start_idx[i][j] = key_value_path["values"]
    #                 range_lengths[i][j] = 1
    #                 fdb_range_nodes[i][j] = [c] * 200
    #     # need to extract the last ranges
    #     self.give_fdb_val_to_node(leaf_path, range_lengths, current_start_idx, fdb_range_nodes, requests_length)

    # def give_fdb_val_to_node(self, leaf_path, range_lengths, current_start_idx, fdb_range_nodes, requests_length):
    #     # print("RANGE LENGTHS")
    #     # print(range_lengths)
    #     # print("CURRENT START IDX")
    #     # print(current_start_idx)
    #     # TODO: change this to accommodate for several requests at once
    #     output_values = self.new_find_fdb_values(leaf_path, range_lengths, current_start_idx, requests_length)
    #     for j in range(requests_length):
    #         for i in range(range_lengths[j]):
    #             n = fdb_range_nodes[j][i]
    #             n.result = output_values[j][i] # TODO: is this true??

    def new_give_fdb_val_to_node(self, leaf_path, range_lengths, current_start_idx, fdb_range_nodes, lat_length):
        # TODO: change this to accommodate for several requests at once
        (output_values, original_indices) = self.newest_find_fdb_values(leaf_path, range_lengths, current_start_idx, lat_length)
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
        # for j in range(lat_length - 1):
        #     for i in range(len(range_lengths[j])):
        #         if current_start_idx[j][i] is not None:
        #             # TODO: need to use original_indices to unmap j and i to the right idxs
        #             for k in range(range_lengths[j][i]):
        #                 # print(output_values)
        #                 n = fdb_range_nodes[j][i][k]
        #                 # print("NOW")
        #                 # print(i)
        #                 # print(j)
        #                 # print(k)
        #                 # print(output_values[j][0][0][i][k])
        #                 n.result = output_values[j][0][0][i][k] # TODO: is this true??

    def find_fdb_values(self, path):
        fdb_request_val = path.pop("values")
        fdb_requests = [(path, [(fdb_request_val, fdb_request_val + 1)])]
        time0 = time.time()
        subxarray = self.fdb.extract(fdb_requests)
        self.time_fdb += time.time() - time0
        output_value = subxarray[0][0][0][0][0]
        return output_value
    
    def new_find_fdb_values(self, path, range_length, current_start_idx):
        fdb_request_val = path.pop("values")
        # print((current_start_idx, current_start_idx + range_length + 1))
        fdb_requests = [(path, [(current_start_idx, current_start_idx + range_length + 1)])]
        # fdb_requests = [(path, new_reqs)]
        time0 = time.time()
        subxarray = self.fdb.extract(fdb_requests)
        self.time_fdb += time.time() - time0
        # output_value = subxarray[0][0][0][0][0]
        output_values = subxarray[0][0][0][0]
        return output_values

    # def new_find_fdb_values(self, path, range_lengths, current_start_idx, requests_length):
    #     fdb_request_val = path.pop("values")
    #     fdb_requests = [(path, [])]
    #     for j in range(requests_length):
    #         current_request_ranges = (current_start_idx[j], current_start_idx[j] + range_lengths[j]+1)
    #         # print(current_request_ranges)
    #         # fdb_requests = [(path, [(current_start_idx, current_start_idx + range_length + 1)])]
    #         fdb_requests[0][1].append(current_request_ranges)
    #     time0 = time.time()
    #     subxarray = self.fdb.extract(fdb_requests)
    #     self.time_fdb += time.time() - time0
    #     # output_value = subxarray[0][0][0][0][0]
    #     output_values = subxarray[0][0][0]
    #     return output_values

    def newest_find_fdb_values(self, path, range_lengths, current_start_idx, lat_length):
        fdb_request_val = path.pop("values")
        # print("NOW INSIDE NEWEST FIND FDB VAL")
        # print(path)
        # fdb_requests = [(path, [])]
        # fdb_requests = list(zip([path]*lat_length, [[]]*lat_length))
        fdb_requests = []
        # print(fdb_requests)
        interm_request_ranges = []
        for i in range(lat_length):
            # fdb_requests[i][1] = []
            for j in range(200):
                if current_start_idx[i][j] is not None:
                    current_request_ranges = (current_start_idx[i][j], current_start_idx[i][j] + range_lengths[i][j])
                    # print(current_request_ranges)
                    # fdb_requests = [(path, [(current_start_idx, current_start_idx + range_length + 1)])]
                    # print(current_request_ranges)
                    interm_request_ranges.append(current_request_ranges)
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        sorted_request_ranges = [item[1] for item in sorted_list]
        original_indices = [item[0] for item in sorted_list]
        fdb_requests.append(tuple((path, sorted_request_ranges)))
        # print(fdb_requests)
        # print(fdb_requests)
        # print("TIME EXTRACT")
        # print(fdb_requests)
        time0 = time.time()
        subxarray = self.fdb.extract(fdb_requests)
        self.time_fdb += time.time() - time0
        # output_value = subxarray[0][0][0][0][0]
        # print(subxarray)
        output_values = subxarray
        # output_values = [[[[[0]*1000]*1000]*1000]]
        return (output_values, original_indices)

    def datacube_natural_indexes(self, axis, subarray):
        indexes = subarray[axis.name]
        return indexes

    def select(self, path, unmapped_path):
        return self.dataarray

    def ax_vals(self, name):
        # for _name, values in self.dataarray.items():
        #     if _name == name:
        #         return values
        return self.dataarray.get(name, None)
