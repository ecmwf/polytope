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
        self.transformation = None
        self.fake_axes = []

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

    def get(self, requests: IndexTree):
        # NOTE: this will do all the transformation unmappings for all the points
        # It doesn't use the tree structure of the result to do the unmapping transformations anymore
        time0 = time.time()
        time_changing_path = 0
        accumulated_fdb_time = 0
        time_change_path = 0
        time_removing_branch = 0
        time_is_nan = 0
        interm_time = 0
        for r in requests.leaves_with_ancestors:
            time5 = time.time()
            # NOTE: Accumulated time in flatten is 0.14s... could be better?
            path = r.flatten_with_ancestors()
            # path = r.flatten()
            time_change_path += time.time() - time5
            path = self.remap_path(path)
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
                time6 = time.time()
                r.remove_branch()
                time_removing_branch += time.time() - time6
        print("FDB TIME")
        print(accumulated_fdb_time)
        print("GET TIME")
        print(time.time() - time0)
        print("TIME FLATTEN PATH AND CHANGE PATH")
        print(time_change_path)
        print("TIME CHANGING PATH")
        print(time_changing_path)
        print("TIME REMOVING BRANCHES")
        print(time_removing_branch)
        print("TIME IS NAN")
        print(time_is_nan)
        print("INTERM TIME")
        print(interm_time)

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
