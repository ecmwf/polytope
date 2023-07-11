import math
import sys
from copy import deepcopy

import numpy as np
import pandas as pd
import xarray as xr

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
}


class XArrayDatacube(Datacube):
    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def _set_mapper(self, values, name):
        if values.dtype.type not in _mappings:
            raise ValueError(f"Could not create a mapper for index type {values.dtype.type} for axis {name}")
        if name in self.options.keys():
            # The options argument here is supposed to be a nested dictionary
            # like {"latitude":{"Cyclic":range}, ...}
            if "Cyclic" in self.options[name].keys():
                value_type = values.dtype.type
                axes_type_str = type(_mappings[value_type]).__name__
                axes_type_str += "Cyclic"
                cyclic_axis_type = deepcopy(getattr(sys.modules["polytope.datacube.datacube_axis"], axes_type_str)())
                self.mappers[name] = cyclic_axis_type
                self.mappers[name].name = name
                self.mappers[name].range = self.options[name]["Cyclic"]
        else:
            self.mappers[name] = deepcopy(_mappings[values.dtype.type])
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

    def __init__(self, dataarray: xr.DataArray, options={}, grid_options={}):
        self.options = options
        self.grid_options = grid_options
        self.grid_mapper = None
        self.axis_counter = 0
        for name in dataarray.dims:
            self._set_grid_mapper(name)
        self.mappers = {}
        for name, values in dataarray.coords.variables.items():
            if name in dataarray.dims:
                self._set_mapper(values, name)
                self.axis_counter += 1
            if self.grid_mapper is not None:
                if name in self.grid_mapper._mapped_axes:
                    self._set_mapper(values, name)
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
                    subxarray = self.dataarray.sel(path, method="nearest")
                    # need to remap the lat, lon in path to dataarray index
                    unmapped_idx = self.grid_mapper.unmap(first_val, second_val)
                    subxarray = subxarray.isel(values=unmapped_idx)
                    value = subxarray.item()
                    key = subxarray.name
                    r.result = (key, value)
                else:
                    # if we have no grid map, still need to assign values
                    subxarray = self.dataarray.sel(path, method="nearest")
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
                    start = indexes.searchsorted(low, "left")  # TODO: catch start=0 (not found)?
                    end = indexes.searchsorted(up, "right")  # TODO: catch end=length (not found)?
                    indexes_between = indexes[start:end].to_list()
            else:
                # Find the range of indexes between lower and upper
                # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
                # Assumes the indexes are already sorted (could sort to be sure) and monotonically increasing
                start = indexes.searchsorted(low, "left")  # TODO: catch start=0 (not found)?
                end = indexes.searchsorted(up, "right")  # TODO: catch end=length (not found)?
                indexes_between = indexes[start:end].to_list()

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

        # Open a view on the subset identified by the path
        subarray = self.dataarray.sel(path, method="nearest")

        # Get the indexes of the axis we want to query
        # XArray does not support branching, so no need to use label, we just take the next axis
        if self.grid_mapper is not None:
            if axis.name == first_axis:
                indexes = []
            elif axis.name == second_axis:
                indexes = []
            else:
                indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
        else:
            indexes = next(iter(subarray.xindexes.values())).to_pandas_index()

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
        subarray = self.dataarray.sel(path)[axis.name]
        subarray_vals = subarray.values
        return index in subarray_vals

    @property
    def axes(self):
        return self.mappers

    def validate(self, axes):
        return validate_axes(self.axes, axes)
