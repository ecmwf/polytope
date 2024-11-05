from copy import deepcopy

import numpy as np
import xarray as xr

from .datacube import Datacube


class XArrayDatacube(Datacube):
    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def __init__(self, dataarray: xr.DataArray, axis_options=None, compressed_axes_options=[], context=None):
        super().__init__(axis_options, compressed_axes_options)
        if axis_options is None:
            axis_options = {}
        self.axis_options = axis_options
        self.axis_counter = 0
        self._axes = None
        self.dataarray = dataarray

        for name, values in dataarray.coords.variables.items():
            options = None
            for opt in self.axis_options:
                if opt.axis_name == name:
                    options = opt
            if name in dataarray.dims:
                self._check_and_add_axes(options, name, values)
                self.treated_axes.append(name)
                self.complete_axes.append(name)
            else:
                if self.dataarray[name].dims == ():
                    self._check_and_add_axes(options, name, values)
                    self.treated_axes.append(name)
        for name in dataarray.dims:
            if name not in self.treated_axes:
                options = None
                for opt in self.axis_options:
                    if opt.axis_name == name:
                        options = opt
                val = dataarray[name].values[0]
                self._check_and_add_axes(options, name, val)
                self.treated_axes.append(name)
        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in self.treated_axes:
                options = None
                for opt in self.axis_options:
                    if opt.axis_name == name:
                        options = opt
                val = self._axes[name].type
                self._check_and_add_axes(options, name, val)

    def get(self, requests, context=None, leaf_path=None, axis_counter=0):
        if context is None:
            context = {}
        if leaf_path is None:
            leaf_path = {}
        if requests.axis.name == "root":
            for c in requests.children:
                self.get(c, context, leaf_path, axis_counter + 1)
        else:
            key_value_path = {requests.axis.name: requests.values}
            ax = requests.axis
            (key_value_path, leaf_path, self.unwanted_path) = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            if len(requests.children) != 0:
                # We are not a leaf and we loop over
                for c in requests.children:
                    self.get(c, context, leaf_path, axis_counter + 1)
            else:
                if self.axis_counter != axis_counter:
                    requests.remove_branch()
                else:
                    # We are at a leaf and need to assign value to it
                    leaf_path_copy = deepcopy(leaf_path)
                    unmapped_path = {}
                    self.refit_path(leaf_path_copy, unmapped_path, leaf_path)
                    for key in leaf_path_copy:
                        leaf_path_copy[key] = list(leaf_path_copy[key])
                    for key in unmapped_path:
                        if isinstance(unmapped_path[key], tuple):
                            unmapped_path[key] = list(unmapped_path[key])
                    subxarray = self.dataarray.sel(leaf_path_copy, method="nearest")
                    subxarray = subxarray.sel(unmapped_path)
                    value = subxarray.values
                    key = subxarray.name
                    requests.result = (key, value)

    def datacube_natural_indexes(self, axis, subarray):
        if axis.name in self.complete_axes:
            indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
        else:
            if subarray[axis.name].values.ndim == 0:
                # NOTE how we handle the two special datetime and timedelta cases to conform with numpy arrays
                if np.issubdtype(subarray[axis.name].values.dtype, np.datetime64):
                    indexes = [subarray[axis.name].astype("datetime64[us]").values]
                elif np.issubdtype(subarray[axis.name].values.dtype, np.timedelta64):
                    indexes = [subarray[axis.name].astype("timedelta64[us]").values]
                else:
                    indexes = [subarray[axis.name].values.tolist()]
            else:
                indexes = subarray[axis.name].values
        return indexes

    def refit_path(self, path_copy, unmapped_path, path):
        for key in path.keys():
            if key not in self.dataarray.dims:
                path_copy.pop(key)
            if key not in self.dataarray.coords.dtypes:
                unmapped_path.update({key: path[key]})
                path_copy.pop(key)
            for key in self.dataarray.coords.dtypes:
                key_dtype = self.dataarray.coords.dtypes[key]
                if key_dtype.type is np.str_ and key in path.keys():
                    unmapped_path.update({key: path[key]})
                    path_copy.pop(key, None)

    def select(self, path, unmapped_path):
        for key in path:
            key_value = path[key][0]
            path[key] = key_value
        for key in unmapped_path:
            key_value = unmapped_path[key][0]
            unmapped_path[key] = key_value
        path_copy = deepcopy(path)
        self.refit_path(path_copy, unmapped_path, path)
        subarray = self.dataarray.sel(path_copy, method="nearest")
        subarray = subarray.sel(unmapped_path)
        return subarray

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
