import importlib
import math
from copy import deepcopy

import xarray as xr

from ...utility.combinatorics import unique, validate_axes
from ..datacube_axis import DatacubeAxis
from ..transformations.datacube_transformations import (
    DatacubeAxisTransformation,
    has_transform,
)
from .datacube import Datacube, DatacubePath, IndexTree


class XArrayDatacube(Datacube):
    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def _create_axes(self, name, values, transformation_type_key, transformation_options):
        # first check what the final axes are for this axis name given transformations
        final_axis_names = DatacubeAxisTransformation.get_final_axes(name, transformation_type_key,
                                                                     transformation_options)
        transformation = DatacubeAxisTransformation.create_transform(name, transformation_type_key,
                                                                     transformation_options)
        for blocked_axis in transformation.blocked_axes():
            self.blocked_axes.append(blocked_axis)
        for axis_name in final_axis_names:
            # if axis does not yet exist, create it

            # first need to change the values so that we have right type
            values = transformation.change_val_type(axis_name, values)
            if axis_name not in self._axes.keys():
                DatacubeAxis.create_standard(axis_name, values, self)
            # add transformation tag to axis, as well as transformation options for later
            setattr(self._axes[axis_name], has_transform[transformation_type_key], True)  # where has_transform is a
            # factory inside datacube_transformations to set the has_transform, is_cyclic etc axis properties
            # add the specific transformation handled here to the relevant axes
            # Modify the axis to update with the tag
            decorator_module = importlib.import_module("polytope.datacube.datacube_axis")
            decorator = getattr(decorator_module, transformation_type_key)
            decorator(self._axes[axis_name])
            if transformation not in self._axes[axis_name].transformations:  # Avoids duplicates being stored
                self._axes[axis_name].transformations.append(transformation)

    def _add_all_transformation_axes(self, options, name, values):
        transformation_options = options["transformation"]
        for transformation_type_key in transformation_options.keys():
            self._create_axes(name, values, transformation_type_key, transformation_options)

    def _check_and_add_axes(self, options, name, values):
        if "transformation" in options:
            self._add_all_transformation_axes(options, name, values)
        else:
            if name not in self.blocked_axes:
                DatacubeAxis.create_standard(name, values, self)

    def __init__(self, dataarray: xr.DataArray, axis_options={}):
        self.axis_options = axis_options
        self.grid_mapper = None
        self.axis_counter = 0
        self._axes = {}
        self.dataarray = dataarray
        treated_axes = []
        self.non_complete_axes = []
        self.complete_axes = []
        self.blocked_axes = []
        self.transformation = {}
        self.fake_axes = []
        for name, values in dataarray.coords.variables.items():
            if name in dataarray.dims:
                options = axis_options.get(name, {})
                self._check_and_add_axes(options, name, values)
                treated_axes.append(name)
                self.complete_axes.append(name)
            else:
                if self.dataarray[name].dims == ():
                    options = axis_options.get(name, {})
                    self._check_and_add_axes(options, name, values)
                    treated_axes.append(name)
                    self.non_complete_axes.append(name)
        for name in dataarray.dims:
            if name not in treated_axes:
                options = axis_options.get(name, {})
                val = dataarray[name].values[0]
                self._check_and_add_axes(options, name, val)
                treated_axes.append(name)

        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        # for name in self._axes:
        #     if name not in treated_axes:
        #         options = axis_options.get(name, {})
        #         val = dataarray[name].values[0]
        #         self._check_and_add_axes(options, name, val)
        # if "longitude" in self._axes:
        #     print(self._axes["longitude"].transformations)

    def _look_up_datacube(self, search_ranges, search_ranges_offset, indexes, axis):
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]
            print(up)
            print(low)
            print(indexes)
            indexes_between = axis.find_indices_between([indexes], low, up, self)
            # Now the indexes_between are values on the cyclic range so need to remap them to their original
            # values before returning them
            for j in range(len(indexes_between)):
                for k in range(len(indexes_between[j])):
                    if offset is None:
                        indexes_between[j][k] = indexes_between[j][k]
                    else:
                        indexes_between[j][k] = round(indexes_between[j][k] + offset, int(-math.log10(axis.tol)))
                    idx_between.append(indexes_between[j][k])
        return idx_between

    def get_indices(self, path: DatacubePath, axis, lower, upper):
        path = self.fit_path(path)
        indexes = axis.find_indexes(path, self)
        print("inside get indices")
        print(indexes)

        search_ranges = axis.remap([lower, upper])
        original_search_ranges = axis.to_intervals([lower, upper])
        # Find the offsets for each interval in the requested range, which we will need later
        search_ranges_offset = []
        for r in original_search_ranges:
            offset = axis.offset(r)
            search_ranges_offset.append(offset)

        idx_between = self._look_up_datacube(search_ranges, search_ranges_offset, indexes, axis)
        # Remove duplicates even if difference of the order of the axis tolerance
        if offset is not None:
            # Note that we can only do unique if not dealing with time values
            idx_between = unique(idx_between)
        return idx_between

    def get(self, requests: IndexTree):
        for r in requests.leaves:
            path = r.flatten()
            if len(path.items()) == self.axis_counter:
                # first, find the grid mapper transform
                unmapped_path = {}
                path_copy = deepcopy(path)
                for key in path_copy:
                    axis = self._axes[key]
                    (path, unmapped_path) = axis.unmap_to_datacube(path, unmapped_path)
                path = self.fit_path(path)
                subxarray = self.dataarray.sel(path, method="nearest")
                subxarray = subxarray.sel(unmapped_path)
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
            path[key] = self._axes[key].remap([value, value])[0][0]
        return path

    def datacube_natural_indexes(self, axis, subarray):
        if axis.name in self.complete_axes:
            indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
        else:
            indexes = [subarray[axis.name].values]
        return indexes

    def fit_path(self, path):
        # path = self.remap_path(path)
        for key in path.keys():
            if key in self.non_complete_axes:
                path.pop(key)
        return path

    def has_index(self, path: DatacubePath, axis, index):
        # when we want to obtain the value of an unsliceable axis, need to check the values does exist in the datacube
        # path = self.fit_path_to_datacube(axis.name, path)[0]
        path = self.fit_path(path)
        indexes = axis.find_indexes(path, self)

        # Open a view on the subset identified by the path
        # subarray = self.dataarray.sel(path, method="nearest")
        # if axis.name in self.transformation.keys():
        #     axis_transforms = self.transformation[axis.name]
        #     already_has_indexes = False
        #     for transform in axis_transforms:
        #         indexes = transform._find_transformed_axis_indices(self, axis, subarray, already_has_indexes)
        #         already_has_indexes = True
        # # return index in subarray_vals
        # else:
        #     indexes = self.datacube_natural_indexes(axis, subarray)
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
