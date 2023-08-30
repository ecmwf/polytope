import math
import os
from copy import deepcopy

from ...utility.combinatorics import unique, validate_axes
from .datacube import Datacube, DatacubePath, IndexTree, configure_datacube_axis
import importlib
from ..datacube_axis import DatacubeAxis
from ..transformations.datacube_transformations import (
    DatacubeAxisTransformation,
    has_transform,
)

# TODO: probably need to do this more general...
os.environ["DYLD_LIBRARY_PATH"] = "/Users/male/build/fdb-bundle/lib"
os.environ["FDB_HOME"] = "/Users/male/git/fdb-home"
import pyfdb  # noqa: E402

# TODO: currently, because the date and time are strings, the data will be treated as an unsliceable axis...


def glue(path, unmap_path):
    return {"t": 0}


def update_fdb_dataarray(fdb_dataarray):
    fdb_dataarray["values"] = [0.0]
    return fdb_dataarray


class FDBDatacube(Datacube):

    def _create_axes(self, name, values, transformation_type_key, transformation_options):
        # first check what the final axes are for this axis name given transformations
        final_axis_names = DatacubeAxisTransformation.get_final_axes(name, transformation_type_key,
                                                                     transformation_options)
        transformation = DatacubeAxisTransformation.create_transform(name, transformation_type_key,
                                                                     transformation_options)
        for blocked_axis in transformation.blocked_axes():
            self.blocked_axes.append(blocked_axis)
        for axis_name in final_axis_names:
            self.complete_axes.append(axis_name)
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
                if name not in self._axes.keys():
                    DatacubeAxis.create_standard(name, values, self)

    def __init__(self, config={}, axis_options={}):
        self.axis_options = axis_options
        self.grid_mapper = None
        self.axis_counter = 0
        self._axes = {}
        treated_axes = []
        self.non_complete_axes = []
        self.complete_axes = []
        self.blocked_axes = []
        self.transformation = {}
        self.fake_axes = []

        partial_request = config
        # Find values in the level 3 FDB datacube
        # Will be in the form of a dictionary? {axis_name:values_available, ...}
        fdb = pyfdb.FDB()
        fdb_dataarray = fdb.axes(partial_request).as_dict()
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
        for r in requests.leaves:
            path = r.flatten()
            if len(path.items()) == self.axis_counter:
                # first, find the grid mapper transform
                unmap_path = {}
                considered_axes = []
                (path, first_val, considered_axes, unmap_path, changed_type_path) = self.fit_path_to_original_datacube(
                    path
                )
                unmap_path.update(changed_type_path)
                # Here, need to give the FDB the path and the unmap_path to select data
                subxarray = glue(path, unmap_path)
                key = list(subxarray.keys())[0]
                value = subxarray[key]
                r.result = (key, value)
            else:
                r.remove_branch()

    def get_mapper(self, axis):
        return self._axes[axis]

    def remap_path(self, path: DatacubePath):
        for key in path:
            value = path[key]
            path[key] = self._axes[key].remap([value, value])[0][0]
        return path
    
    def _look_up_datacube(self, search_ranges, search_ranges_offset, indexes, axis):
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]
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

    def fit_path_to_original_datacube(self, path):
        path = self.remap_path(path)
        first_val = None
        unmap_path = {}
        considered_axes = []
        changed_type_path = {}
        for axis_name in self.transformation.keys():
            axis_transforms = self.transformation[axis_name]
            for transform in axis_transforms:
                (path, temp_first_val, considered_axes, unmap_path, changed_type_path) = transform._adjust_path(
                    path, considered_axes, unmap_path, changed_type_path
                )
                if temp_first_val:
                    first_val = temp_first_val
        return (path, first_val, considered_axes, unmap_path, changed_type_path)
    
    def get_indices(self, path: DatacubePath, axis, lower, upper):
        path = self.fit_path(path)
        indexes = axis.find_indexes(path, self)
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

    def datacube_natural_indexes(self, axis, subarray):
        indexes = subarray[axis.name]
        return indexes

    def select(self, path, unmapped_path):
        return self.dataarray

    def has_index(self, path: DatacubePath, axis, index):
        # when we want to obtain the value of an unsliceable axis, need to check the values does exist in the datacube
        # subarray_vals = self.dataarray[axis.name]
        path = self.fit_path(path)
        indexes = axis.find_indexes(path, self)
        # return index in subarray_vals
        return index in indexes

    @property
    def axes(self):
        return self._axes

    def fit_path(self, path):
        for key in path.keys():
            if key not in self.complete_axes:
                path.pop(key)
        return path

    def validate(self, axes):
        return validate_axes(self.axes, axes)

    def ax_vals(self, name):
        for _name, values in self.dataarray.items():
            if _name == name:
                return values
