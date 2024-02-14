from copy import deepcopy

import numpy as np
import xarray as xr

from .datacube import Datacube, IndexTree


class XArrayDatacube(Datacube):
    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def __init__(self, dataarray: xr.DataArray, axis_options=None, datacube_options=None):
        if axis_options is None:
            axis_options = {}
        if datacube_options is None:
            datacube_options = {}
        self.axis_options = axis_options
        self.axis_counter = 0
        self._axes = None
        self.dataarray = dataarray
        treated_axes = []
        self.complete_axes = []
        self.blocked_axes = []
        self.fake_axes = []
        self.nearest_search = None
        self.coupled_axes = []
        self.axis_with_identical_structure_after = datacube_options.get("identical structure after")
        self.transformed_axes = []
        # self.is_xarray = True

        for name, values in dataarray.coords.variables.items():
            if name in dataarray.dims:
                options = axis_options.get(name, None)
                self._check_and_add_axes(options, name, values)
                treated_axes.append(name)
                self.complete_axes.append(name)
            else:
                if self.dataarray[name].dims == ():
                    options = axis_options.get(name, None)
                    self._check_and_add_axes(options, name, values)
                    treated_axes.append(name)
        for name in dataarray.dims:
            if name not in treated_axes:
                options = axis_options.get(name, None)
                val = dataarray[name].values[0]
                self._check_and_add_axes(options, name, val)
                treated_axes.append(name)
        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in treated_axes:
                options = axis_options.get(name, None)
                val = self._axes[name].type
                self._check_and_add_axes(options, name, val)

    def get(self, requests: IndexTree):
        for r in requests.leaves:
            path = r.flatten()
            if len(path.items()) == self.axis_counter:
                # first, find the grid mapper transform
                unmapped_path = {}
                path_copy = deepcopy(path)
                for key in path_copy:
                    axis = self._axes[key]
                    key_value_path = {key: path_copy[key]}
                    # (path, unmapped_path) = axis.unmap_to_datacube(path, unmapped_path)
                    (key_value_path, path, unmapped_path) = axis.unmap_path_key(
                            key_value_path, path, unmapped_path
                            )
                path.update(key_value_path)
                path.update(unmapped_path)

                unmapped_path = {}
                for key in path.keys():
                    if key not in self.dataarray.dims:
                        path.pop(key)
                    if key not in self.dataarray.coords.dtypes:
                        unmapped_path.update({key: path[key]})
                        path.pop(key)
                    for key in self.dataarray.coords.dtypes:
                        key_dtype = self.dataarray.coords.dtypes[key]
                        if key_dtype.type is np.str_ and key in path.keys():
                            unmapped_path.update({key: path[key]})
                            path.pop(key)

                subxarray = self.dataarray.sel(path, method="nearest")
                subxarray = subxarray.sel(unmapped_path)
                value = subxarray.item()
                key = subxarray.name
                r.result = (key, value)
            else:
                r.remove_branch()

    def datacube_natural_indexes(self, axis, subarray):
        if axis.name in self.complete_axes:
            indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
        else:
            if subarray[axis.name].values.ndim == 0:
                indexes = [subarray[axis.name].values]
            else:
                indexes = subarray[axis.name].values
        return indexes

    def select(self, path, unmapped_path):
        subarray = self.dataarray.sel(path, method="nearest")
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
