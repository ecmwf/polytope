import math

import xarray as xr
from copy import deepcopy

from ...utility.combinatorics import unique, validate_axes
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
        self.blocked_axes = []
        self.transformation = {}
        for name, values in dataarray.coords.variables.items():
            if name in dataarray.dims:
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
            if len(path.items()) == self.axis_counter:
                # first, find the grid mapper transform
                unmap_path = {}
                considered_axes = []
                for key in path.keys():
                    (path, first_val, considered_axes, unmap_path) = self.fit_path_to_datacube(
                        key, path, considered_axes, unmap_path
                    )
                    considered_axes.append(key)
                subxarray = self.dataarray.sel(path, method="nearest")
                subxarray = subxarray.sel(unmap_path)
                value = subxarray.item()
                key = subxarray.name
                r.result = (key, value)
            else:
                r.remove_branch()

    def get_mapper(self, axis):
        return self._axes[axis]

    # TODO: should this be in DatacubePath?
    def remap_path(self, path: DatacubePath):
        for key in path:
            value = path[key]
            path[key] = self._axes[key].remap_val_to_axis_range(value)
        return path

    def _find_indexes_between(self, axis, indexes, low, up):
        if axis.name in self.complete_axes:
            # Find the range of indexes between lower and upper
            # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
            # Assumes the indexes are already sorted (could sort to be sure) and monotonically increasing
            start = indexes.searchsorted(low, "left")
            end = indexes.searchsorted(up, "right")
            indexes_between = indexes[start:end].to_list()
        else:
            indexes_between = [i for i in indexes if low <= i <= up]
        return indexes_between

    def _look_up_datacube(self, search_ranges, search_ranges_offset, indexes, axis, first_val):
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]
            if axis.name in self.transformation.keys():
                axis_transforms = self.transformation[axis.name]
                temp_indexes = deepcopy(indexes)
                for transform in axis_transforms:
                    # indexes_between = transform._find_transformed_indices_between(
                    #     axis, self, indexes, low, up, first_val
                    # )
                    temp_indexes = transform._find_transformed_indices_between(
                        axis, self, temp_indexes, low, up, first_val
                    )
                indexes_between = temp_indexes
            else:
                indexes_between = self._find_indexes_between(axis, indexes, low, up)
            # Now the indexes_between are values on the cyclic range so need to remap them to their original
            # values before returning them
            for j in range(len(indexes_between)):
                if offset is None:
                    indexes_between[j] = indexes_between[j]
                else:
                    indexes_between[j] = round(indexes_between[j] + offset, int(-math.log10(axis.tol)))
                idx_between.append(indexes_between[j])
        return idx_between

    def datacube_natural_indexes(self, axis, subarray):
        if axis.name in self.complete_axes:
            indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
        else:
            indexes = [subarray[axis.name].values]
        return indexes

    def fit_path_to_datacube(self, axis_name, path, considered_axes=[], unmap_path={}):
        # TODO: how to make this also work for the get method?
        path = self.remap_path(path)
        for key in path.keys():
            if self.dataarray[key].dims == ():
                path.pop(key)
        first_val = None
        if axis_name in self.transformation.keys():
            axis_transforms = self.transformation[axis_name]
            for transform in axis_transforms:
                (path, first_val, considered_axes, unmap_path) = transform._adjust_path(
                    path, considered_axes, unmap_path
                )
        return (path, first_val, considered_axes, unmap_path)

    def get_indices(self, path: DatacubePath, axis, lower, upper):
        (path, first_val, considered_axes, unmap_path) = self.fit_path_to_datacube(axis.name, path)
        # Open a view on the subset identified by the path
        subarray = self.dataarray.sel(path, method="nearest")
        # Get the indexes of the axis we want to query
        # XArray does not support branching, so no need to use label, we just take the next axis
        if axis.name in self.transformation.keys():
            axis_transforms = self.transformation[axis.name]
            for transform in axis_transforms:
                # TODO: put this within the transform as transformed_indices method
                indexes = transform._find_transformed_axis_indices(self, axis, subarray)
        else:
            indexes = self.datacube_natural_indexes(axis, subarray)
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
        path = self.fit_path_to_datacube(axis, path)[0]

        # Open a view on the subset identified by the path
        subarray = self.dataarray.sel(path, method="nearest")
        if axis.name in self.transformation.keys():
            axis_transforms = self.transformation[axis.name]
            for transform in axis_transforms:
                indexes = transform._find_transformed_axis_indices(self, axis, subarray)
        # return index in subarray_vals
        else:
            indexes = self.datacube_natural_indexes(axis, subarray)
        return index in indexes

    @property
    def axes(self):
        return self._axes

    def validate(self, axes):
        return validate_axes(list(self.axes.keys()), axes)

    def ax_vals(self, name):
        treated_axes = []
        for _name, values in self.dataarray.coords.variables.items():
            treated_axes.append(_name)
            if _name == name:
                return values.values
        for _name in self.dataarray.dims:
            if _name not in treated_axes:
                if _name == name:
                    return self.dataarray[name].values[0]
