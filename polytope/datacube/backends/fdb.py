import logging
from copy import deepcopy
from itertools import product
import time
import operator

from ...utility.geometry import nearest_pt
from .datacube import Datacube, TensorIndexTree


class FDBDatacube(Datacube):
    def __init__(self, gj, request, config=None, axis_options=None, compressed_axes_options=[]):
        if config is None:
            config = {}

        super().__init__(axis_options, compressed_axes_options)

        logging.info("Created an FDB datacube with options: " + str(axis_options))

        self.unwanted_path = {}
        self.axis_options = axis_options

        partial_request = config
        # Find values in the level 3 FDB datacube

        self.gj = gj
        self.unmapping_time = 0
        self.request_sorting_time = 0
        self.bunching_up_request_time = 0
        self.appending_info_time = 0
        self.sorting_time = 0

        time0 = time.time()
        self.fdb_coordinates = self.gj.axes(partial_request)
        print("GJ AXES TIME")
        print(time.time()-time0)

        self.check_branching_axes(request)

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

    def check_branching_axes(self, request):
        polytopes = request.polytopes()
        for polytope in polytopes:
            for ax in polytope._axes:
                if ax == "levtype":
                    (upper, lower, idx) = polytope.extents(ax)
                    if "sfc" in polytope.points[idx]:
                        self.fdb_coordinates.pop("levelist")
        self.fdb_coordinates.pop("quantile", None)

    def get(self, requests: TensorIndexTree):
        time4 = time.time()
        if len(requests.children) == 0:
            return requests
        fdb_requests = []
        fdb_requests_decoding_info = []
        self.get_fdb_requests(requests, fdb_requests, fdb_requests_decoding_info)

        # here, loop through the fdb requests and request from gj and directly add to the nodes

        total_request_decoding_info = []
        total_uncompressed_requests = []
        time0 = time.time()
        # print("THE COMPRESSED REQUESTS HERE")
        # print(fdb_requests)
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
                complete_uncompressed_request = (uncompressed_request, compressed_request[1])
                # here, accumulate requests to extract all at the same time
                total_uncompressed_requests.append(complete_uncompressed_request)
                total_request_decoding_info.append(fdb_requests_decoding_info[j])
        # print(total_uncompressed_requests)
        print("UNCOMPRESS AND FLATTEN TREE")
        print(time.time() - time0)
        time1 = time.time()
        output_values = self.gj.extract(total_uncompressed_requests)
        # print(total_uncompressed_requests)
        print("GJ TIME")
        print(time.time() - time1)
        # print(output_values)
        time2 = time.time()
        self.assign_fdb_output_to_nodes(output_values, total_request_decoding_info)
        print("ASSIGN GJ DATA TO RIGHT NODES")
        print(time.time() - time2)
        print("UNMAPPING TIME")
        print(self.unmapping_time)
        print("REQUEST SORTING TIME")
        print(self.request_sorting_time)
        print("BUNCH REQUESTS TIME AT LAT")
        print(self.bunching_up_request_time)
        print("APPENDING INFO TIME")
        print(self.appending_info_time)
        print("TOTAL GET TIME")
        print(time.time() - time4)
        print("SORTING TIME")
        print(self.sorting_time)

    def get_fdb_requests(
        self, requests: TensorIndexTree, fdb_requests=[], fdb_requests_decoding_info=[], leaf_path=None,
    ):
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
            time0 = time.time()
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            self.unmapping_time += time.time() - time0
            leaf_path.update(key_value_path)
            if len(requests.children[0].children[0].children) == 0:
                # find the fdb_requests and associated nodes to which to add results
                time2 = time.time()
                (path, range_lengths, current_start_idxs, fdb_node_ranges, lat_length) = self.get_2nd_last_values(
                    requests, leaf_path
                )
                self.bunching_up_request_time += time.time() - time2
                time1 = time.time()
                # print("AND NOW LOOK NOW")
                # print(current_start_idxs)
                (original_indices, sorted_request_ranges, fdb_node_ranges, current_start_idxs) = self.sort_fdb_request_ranges(
                    range_lengths, current_start_idxs, lat_length, fdb_node_ranges
                )
                self.request_sorting_time += time.time() - time1
                time3 = time.time()
                fdb_requests.append((path, sorted_request_ranges))
                fdb_requests_decoding_info.append(
                    (original_indices, fdb_node_ranges, lat_length, range_lengths, current_start_idxs)
                )
                self.appending_info_time += time.time() - time3

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

            if first_ax_name not in self.nearest_search.keys() or second_ax_name not in self.nearest_search.keys():
                raise Exception("nearest point search axis are wrong")

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
                    possible_lons = [latlon[1] for latlon in nearest_latlons if (latlon[0],) == lat_child.values]
                    lon_children_values = [child.values for child in lat_child.children]
                    for j in range(len(lon_children_values)):
                        lon_child_val = lon_children_values[j]
                        lon_child = [child for child in lat_child.children if child.values == lon_child_val][0]
                        for value in lon_child.values:
                            if value not in possible_lons:
                                lon_child.remove_compressed_branch(value)

        lat_length = len(requests.children)
        # range_lengths = [False] * lat_length
        current_start_idxs = [False] * lat_length
        fdb_node_ranges = [False] * lat_length
        for i in range(len(requests.children)):
            lat_child = requests.children[i]
            lon_length = len(lat_child.children)
            # range_lengths[i] = [1] * lon_length
            current_start_idxs[i] = [None] * lon_length
            fdb_node_ranges[i] = [[TensorIndexTree.root] * lon_length] * lon_length
            # range_length = deepcopy(range_lengths[i])
            current_start_idx = deepcopy(current_start_idxs[i])
            fdb_range_nodes = deepcopy(fdb_node_ranges[i])
            key_value_path = {lat_child.axis.name: lat_child.values}
            ax = lat_child.axis
            time0 = time.time()
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            self.unmapping_time += time.time() - time0
            self.bunching_up_request_time -= time.time() - time0
            leaf_path.update(key_value_path)
            (current_start_idxs[i], fdb_node_ranges[i]) = self.get_last_layer_before_leaf(
                lat_child, leaf_path, current_start_idx, fdb_range_nodes
            )

        leaf_path_copy = deepcopy(leaf_path)
        leaf_path_copy.pop("values", None)
        # print("AND NOW")
        # print(current_start_idxs)
        # print(fdb_node_ranges)
        return (leaf_path_copy, [], current_start_idxs, fdb_node_ranges, lat_length)

    def get_last_layer_before_leaf(self, requests, leaf_path, current_idx, fdb_range_n):
        i = 0
        current_idx = []
        fdb_range_n = []
        for c in requests.children:
            # now c are the leaves of the initial tree
            key_value_path = {c.axis.name: c.values}
            # print("NOW LOOK")
            # print(c.values)
            ax = c.axis
            time0 = time.time()
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            self.unmapping_time += time.time() - time0
            self.bunching_up_request_time -= time.time() - time0
            # print(key_value_path)
            # TODO: change this to accommodate non consecutive indexes being compressed too
            # range_l = [len(c.values)]
            current_idx.extend(key_value_path["values"])
            # fdb_range_n[i] = [c]*len(c.values)
            for j in range(len(c.values)):
                fdb_range_n.append([c])
            # fdb_range_n.append([c]*len(c.values))
            # print("NOW NOW")
            # print(fdb_range_n[i])
            # leaf_path.update(key_value_path)
            # last_idx = key_value_path["values"]
            # if current_idx[i] is None:
            #     current_idx[i] = last_idx
            #     fdb_range_n[i][range_l[i] - 1] = c
            # else:
            #     if last_idx == current_idx[i] + range_l[i]:
            #         range_l[i] += 1
            #         fdb_range_n[i][range_l[i] - 1] = c
            #     else:
            #         key_value_path = {c.axis.name: c.values}
            #         ax = c.axis
            #         (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
            #             key_value_path, leaf_path, self.unwanted_path
            #         )
            #         leaf_path.update(key_value_path)
            #         i += 1
            #         current_start_idx = key_value_path["values"]
            #         current_idx[i] = current_start_idx
        # print("NOW NOW")
        # print(fdb_range_n)
        return (current_idx, fdb_range_n)

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
            # print(output_values)
            # new_fdb_range_nodes = []
            # print("NOW")
            # print(original_indices)
            # TODO: what happens when we remove sorting?
            # time1 = time.time()
            sorted_fdb_range_nodes = [fdb_node_ranges[i] for i in original_indices]
            sorted_current_start_idxs = [current_start_idxs[i] for i in original_indices]
            # print(time.time() - time1)
            # self.sorting_time +=time.time() - time1
            # time1 = time.time()
            # print("LOOK NOW REALLY")
            # print(fdb_node_ranges)
            # print(current_start_idxs)
            for i in range(len(sorted_fdb_range_nodes)):
                # for k in range(sorted_range_lengths[i]):
                n = sorted_fdb_range_nodes[i]
                # interm_request_output_values = request_output_values[0][i][0]
                # TODO: k again??
                for j in range(len(sorted_current_start_idxs[i])):
                    # n = sorted_fdb_range_nodes[i]
                    m = n[j][0]
                    # time1 = time.time()
                    m.result.append(request_output_values[0][i][0][j])
                    # self.sorting_time += time.time() - time1

    def sort_fdb_request_ranges(self, range_lengths, current_start_idx, lat_length, fdb_node_ranges):
        # print("WHAT IS THE CURREENT START IDX")
        # print(current_start_idx)
        interm_request_ranges = []
        # print("WHAT ARE THE NODE RANGES?")
        # print(fdb_node_ranges)
        # TODO: modify the start indexes to have as many arrays as the request ranges
        new_fdb_node_ranges = []
        new_current_start_idx = []
        for i in range(lat_length):
            interm_fdb_nodes = fdb_node_ranges[i]
            interm_start_idx = current_start_idx[i]
            # print("WHAT IS THE CURREENT START IDX")
            # print(interm_start_idx)
            # for j in range(len(range_lengths[i])):
            if True:
                # if current_start_idx[i][0] is not None:
                if True:
                    # print(current_start_idx[i][-1]+1 - current_start_idx[i][0])
                    # print(len(current_start_idx[i]))
                    if abs(current_start_idx[i][-1]+1 - current_start_idx[i][0]) <= len(current_start_idx[i]):
                        # print("WE DID NOT DIVIDE THE IDX RANGES")
                        current_request_ranges = (current_start_idx[i][0], current_start_idx[i][-1]+1)
                        # print(current_request_ranges)
                        interm_request_ranges.append(current_request_ranges)
                        new_fdb_node_ranges.append(interm_fdb_nodes)
                        new_current_start_idx.append(interm_start_idx)
                    else:
                        time0 = time.time()
                        # TODO: see where we have jump in indices and separate the ranges there
                        jumps = list(map(operator.sub, current_start_idx[i][1:], current_start_idx[i][:-1]))
                        last_idx = 0
                        for j, jump in enumerate(jumps):
                            # new_interm_fdb_nodes = []
                            # new_interm_start_idx = []
                            if jump > 1:
                                current_request_ranges = (current_start_idx[i][last_idx], current_start_idx[i][j]+1)
                                # new_interm_fdb_nodes.append(interm_fdb_nodes[last_idx:j + 1])
                                # new_interm_start_idx.append(interm_start_idx[last_idx:j + 1])
                                new_fdb_node_ranges.append(interm_fdb_nodes[last_idx:j + 1])
                                new_current_start_idx.append(interm_start_idx[last_idx:j + 1])
                                last_idx = j+1
                                interm_request_ranges.append(current_request_ranges)
                                # print("DID WE NOT ADD HERE?")
                                # print(new_interm_start_idx)
                                # print(interm_fdb_nodes)
                                # print(last_idx)
                                # print(j)
                                # new_interm_fdb_nodes.append(interm_fdb_nodes[last_idx:j])
                                # new_interm_start_idx.append(interm_start_idx[last_idx:j])
                            if j == len(current_start_idx[i]) - 2:
                                current_request_ranges = (current_start_idx[i][last_idx], current_start_idx[i][-1]+1)
                                interm_request_ranges.append(current_request_ranges)
                                # new_interm_fdb_nodes.append(interm_fdb_nodes[last_idx:])
                                # new_interm_start_idx.append(interm_start_idx[last_idx:])
                                new_fdb_node_ranges.append(interm_fdb_nodes[last_idx:])
                                new_current_start_idx.append(interm_start_idx[last_idx:])
                        print("TIME FOR CONSTRUCTING THE JUMP RANGES")
                        print(time.time() - time0)
        request_ranges_with_idx = list(enumerate(interm_request_ranges))
        sorted_list = sorted(request_ranges_with_idx, key=lambda x: x[1][0])
        original_indices, sorted_request_ranges = zip(*sorted_list)
        # print("INSIDE THE SORTING PROBLEM?")
        # print(sorted_request_ranges)
        # print(new_current_start_idx)
        # print(new_fdb_node_ranges)
        return (original_indices, sorted_request_ranges, new_fdb_node_ranges, new_current_start_idx)

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
