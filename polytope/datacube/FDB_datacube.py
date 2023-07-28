import math
import sys
from copy import deepcopy

import numpy as np
import pandas as pd
import pyfdb

from ..utility.combinatorics import unique, validate_axes
from .datacube import Datacube, DatacubePath, IndexTree
from .datacube_axis import (
    FloatAxis,
    IntAxis,
    PandasTimedeltaAxis,
    PandasTimestampAxis,
    UnsliceableaAxis,
)
from .mappers import OctahedralGridMap

_mappings = {
    pd.Int64Dtype: IntAxis(),
    pd.Timestamp: PandasTimestampAxis(),
    np.int64: IntAxis(),
    np.datetime64: PandasTimestampAxis(),
    np.timedelta64: PandasTimedeltaAxis(),
    np.float64: FloatAxis(),
    np.str_: UnsliceableaAxis(),
    str: UnsliceableaAxis(),
    np.object_: UnsliceableaAxis(),
    "int" : IntAxis(),
    "float" : FloatAxis(),
}


def get_datacube_indices(partial_request):
    datacube_dico = {"step": [0, 3, 6],
                     "level" : [10, 11, 12],
                     "values": [1, 2, 3, 4]}
    return datacube_dico


def glue(path):
    return {"t" : 0}


def update_fdb_dataarray(fdb_dataarray):
    new_dict = {}
    for key, values in fdb_dataarray.items():
        if key in ["levelist", "param", "step"]:
            new_values = []
            for val in values:
                new_values.append(int(val))
            new_dict[key] = new_values
        elif key == "date":
            time = fdb_dataarray["time"][0]
            time = time + "00"
            new_val = [fdb_dataarray[key][0] + "T" + time]
            new_dict[key] = new_val
        elif key == "time":
            pass
        else:
            new_dict[key] = values
    new_dict["values"] = [0.0]


class FDBDatacube(Datacube):

    def _set_mapper(self, values, name):
        if type(values[0]).__name__ not in _mappings:
            raise ValueError(f"Could not create a mapper for index type {type(values[0]).__name__} for axis {name}")
        if name in self.options.keys():
            # The options argument here is supposed to be a nested dictionary
            # like {"latitude":{"Cyclic":range}, ...}
            if "Cyclic" in self.options[name].keys():
                axes_type_str = type(values[0]).__name__
                axes_type_str += "Cyclic"
                cyclic_axis_type = deepcopy(getattr(sys.modules["polytope.datacube.datacube_axis"], axes_type_str)())
                self.mappers[name] = cyclic_axis_type
                self.mappers[name].name = name
                self.mappers[name].range = self.options[name]["Cyclic"]
        else:
            self.mappers[name] = deepcopy(_mappings[type(values[0]).__name__])
            self.mappers[name].name = name

    def _set_grid_mapper(self, name):
        if name in self.grid_options.keys():
            if "grid_map" in self.grid_options[name].keys():
                grid_mapping_options = self.grid_options[name]["grid_map"]
                grid_type = grid_mapping_options["type"]
                grid_axes = grid_mapping_options["axes"]
                if grid_type[0] == "octahedral":
                    resolution = grid_type[1]
                    self.grid_mapper = OctahedralGridMap(name, grid_axes, resolution)

    def __init__(self, config={}, options={}, grid_options={}):
        # Need to get the cyclic options and grid options from somewhere
        self.options = options
        self.grid_options = grid_options

        self.grid_mapper = None
        self.axis_counter = 0
        for name in self.grid_options.keys():
            self._set_grid_mapper(name)
        self.mappers = {}

        partial_request = config
        # Find values in the level 3 FDB datacube
        # Will be in the form of a dictionary? {axis_name:values_available, ...}
        # dataarray = get_datacube_indices(partial_request)
        fdb = pyfdb.FDB()
        fdb_dataarray = fdb.axes(partial_request).as_dict()
        dataarray = update_fdb_dataarray(fdb_dataarray)

        for name, values in dataarray.items():
            values.sort()
            self._set_mapper(values, name)
            self.axis_counter += 1
            if self.grid_mapper is not None:
                if name == self.grid_mapper._base_axis:
                    # Need to remove the base axis and replace with the mapped grid axes
                    del self.mappers[name]
                    self.axis_counter -= 1
                    for axis_name in self.grid_mapper._mapped_axes:
                        self._set_mapper(self.grid_mapper._value_type, axis_name)
                        self.axis_counter += 1
        self.dataarray = dataarray

    def get(self, requests: IndexTree):
        for r in requests.leaves:
            path = r.flatten()
            path = self.remap_path(path)
            if len(path.items()) == self.axis_counter:
                if self.grid_mapper is not None:
                    first_axis = self.grid_mapper._mapped_axes[0]
                    first_val = path[first_axis]
                    second_axis = self.grid_mapper._mapped_axes[1]
                    second_val = path[second_axis]
                    path.pop(first_axis, None)
                    path.pop(second_axis, None)
                    # need to remap the lat, lon in path to dataarray index
                    unmapped_idx = self.grid_mapper.unmap(first_val, second_val)
                    path[self.grid_mapper._base_axis] = unmapped_idx
                    # Ask FDB what values it has on the path
                    subxarray = glue(path)
                    key = list(subxarray.keys())[0]
                    value = subxarray[key]
                    r.result = (key, value)
                else:
                    # if we have no grid map, still need to assign values
                    subxarray = glue(path)
                    value = subxarray.item()
                    key = subxarray.name
                    r.result = (key, value)
            else:
                r.remove_branch()

    def get_mapper(self, axis):
        return self.mappers[axis]

    def remap_path(self, path: DatacubePath):
        for key in path:
            value = path[key]
            path[key] = self.mappers[key].remap_val_to_axis_range(value)
        return path

    def _look_up_datacube(self, search_ranges, search_ranges_offset, indexes, axis, first_val):
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]

            if self.grid_mapper is not None:
                first_axis = self.grid_mapper._mapped_axes[0]
                second_axis = self.grid_mapper._mapped_axes[1]
                if axis.name == first_axis:
                    indexes_between = self.grid_mapper.map_first_axis(low, up)
                elif axis.name == second_axis:
                    indexes_between = self.grid_mapper.map_second_axis(first_val, low, up)
                else:
                    indexes_between = [i for i in indexes if low <= i <= up]
            else:
                indexes_between = [i for i in indexes if low <= i <= up]

            # Now the indexes_between are values on the cyclic range so need to remap them to their original
            # values before returning them
            for j in range(len(indexes_between)):
                if offset is None:
                    indexes_between[j] = indexes_between[j]
                else:
                    indexes_between[j] = round(indexes_between[j] + offset, int(-math.log10(axis.tol)))

                idx_between.append(indexes_between[j])
        return idx_between

    def get_indices(self, path: DatacubePath, axis, lower, upper):
        path = self.remap_path(path)
        first_val = None
        if self.grid_mapper is not None:
            first_axis = self.grid_mapper._mapped_axes[0]
            first_val = path.get(first_axis, None)
            second_axis = self.grid_mapper._mapped_axes[1]
            path.pop(first_axis, None)
            path.pop(second_axis, None)
            if axis.name == first_axis:
                indexes = []
            elif axis.name == second_axis:
                indexes = []
            else:
                indexes = self.dataarray[axis.name]
        else:
            indexes = self.dataarray[axis.name]

        # Here, we do a cyclic remapping so we look up on the right existing values in the cyclic range on the datacube
        search_ranges = axis.remap([lower, upper])
        original_search_ranges = axis.to_intervals([lower, upper])

        # Find the offsets for each interval in the requested range, which we will need later
        search_ranges_offset = []
        for r in original_search_ranges:
            offset = axis.offset(r)
            search_ranges_offset.append(offset)

        # Look up the values in the datacube for each cyclic interval range
        idx_between = self._look_up_datacube(search_ranges, search_ranges_offset, indexes, axis, first_val)

        # Remove duplicates even if difference of the order of the axis tolerance
        if offset is not None:
            # Note that we can only do unique if not dealing with time values
            idx_between = unique(idx_between)

        return idx_between

    def has_index(self, path: DatacubePath, axis, index):
        # when we want to obtain the value of an unsliceable axis, need to check the values does exist in the datacube
        subarray_vals = self.dataarray[axis.name]
        return index in subarray_vals

    @property
    def axes(self):
        return self.mappers

    def validate(self, axes):
        return validate_axes(self.axes, axes)
