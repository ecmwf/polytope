import math

import xarray as xr

from ..utility.combinatorics import unique, validate_axes
from .datacube import Datacube, DatacubePath, IndexTree, configure_datacube_axis


class XArrayDatacube(Datacube):
    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def __init__(self, dataarray: xr.DataArray, axis_options={}):
        self.axis_options = axis_options
        self.grid_mapper = None
        self.axis_counter = 0
        self._axes = {}
        self.dataarray = dataarray
        treated_axes = []
        self.complete_axes = []
        for name, values in dataarray.coords.variables.items():
            if name in dataarray.dims:
                self.dataarray = self.dataarray.sortby(name)
                options = axis_options.get(name, {})
                configure_datacube_axis(options, name, values, self)
                treated_axes.append(name)
                self.complete_axes.append(name)
            else:
                if self.dataarray[name].dims == ():
                    options = axis_options.get(name, {})
                    configure_datacube_axis(options, name, values, self)
                    treated_axes.append(name)
        for name in dataarray.dims:
            if name not in treated_axes:
                options = axis_options.get(name, {})
                val = dataarray[name].values[0]
                configure_datacube_axis(options, name, val, self)

    def get(self, requests: IndexTree):
        for r in requests.leaves:
            path = r.flatten()
            path = self.remap_path(path)
            if len(path.items()) == self.axis_counter:
                for key in path.keys():
                    if self.dataarray[key].dims == ():
                        path.pop(key)
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
        return self._axes[axis]

    def remap_path(self, path: DatacubePath):
        for key in path:
            value = path[key]
            path[key] = self._axes[key].remap_val_to_axis_range(value)
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
                    if axis.name in self.complete_axes:
                        start = indexes.searchsorted(low, "left")
                        end = indexes.searchsorted(up, "right")
                        indexes_between = indexes[start:end].to_list()
                    else:
                        indexes_between = [i for i in indexes if low <= i <= up]
                    # start = indexes.searchsorted(low, "left")  # TODO: catch start=0 (not found)?
                    # end = indexes.searchsorted(up, "right")  # TODO: catch end=length (not found)?
                    # indexes_between = indexes[start:end].to_list()
            else:
                # Find the range of indexes between lower and upper
                # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
                # Assumes the indexes are already sorted (could sort to be sure) and monotonically increasing
                # start = indexes.searchsorted(low, "left")  # TODO: catch start=0 (not found)?
                # end = indexes.searchsorted(up, "right")  # TODO: catch end=length (not found)?
                # indexes_between = indexes[start:end].to_list()
                if axis.name in self.complete_axes:
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    indexes_between = indexes[start:end].to_list()
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
        for key in path.keys():
            if self.dataarray[key].dims == ():
                path.pop(key)

        first_val = None
        if self.grid_mapper is not None:
            first_axis = self.grid_mapper._mapped_axes[0]
            first_val = path.get(first_axis, None)
            second_axis = self.grid_mapper._mapped_axes[1]
            path.pop(first_axis, None)
            path.pop(second_axis, None)

        for key in path.keys():
            if self.dataarray[key].dims == ():
                path.pop(key)

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
                # assert axis.name == next(iter(subarray.xindexes))
                # indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
                if axis.name in self.complete_axes:
                    # indexes = list(subarray.indexes[axis.name])
                    indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
                else:
                    indexes = [subarray[axis.name].values]
        else:
            if axis.name in self.complete_axes:
                # indexes = list(subarray.indexes[axis.name])
                indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
            else:
                indexes = [subarray[axis.name].values]
            # assert axis.name == next(iter(subarray.xindexes))
            # indexes = next(iter(subarray.xindexes.values())).to_pandas_index()

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
        return self._axes

    def validate(self, axes):
        return validate_axes(list(self.axes.keys()), axes)
