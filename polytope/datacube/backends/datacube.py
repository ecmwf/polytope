import importlib
import math
from abc import ABC, abstractmethod
from typing import Any

import xarray as xr

from ...utility.combinatorics import unique, validate_axes
from ..datacube_axis import DatacubeAxis
from ..index_tree import DatacubePath, IndexTree
from ..transformations.datacube_transformations import (
    DatacubeAxisTransformation,
    has_transform,
)


class Datacube(ABC):
    @abstractmethod
    def get(self, requests: IndexTree) -> Any:
        """Return data given a set of request trees"""

    @property
    def axes(self):
        return self._axes

    def validate(self, axes):
        """returns true if the input axes can be resolved against the datacube axes"""
        return validate_axes(list(self.axes.keys()), axes)

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

    def has_index(self, path: DatacubePath, axis, index):
        "Given a path to a subset of the datacube, checks if the index exists on that sub-datacube axis"
        path = self.fit_path(path)
        indexes = axis.find_indexes(path, self)
        return index in indexes

    def fit_path(self, path):
        for key in path.keys():
            if key not in self.complete_axes:
                path.pop(key)
        return path

    def get_indices(self, path: DatacubePath, axis, lower, upper, method=None):
        """
        Given a path to a subset of the datacube, return the discrete indexes which exist between
        two non-discrete values (lower, upper) for a particular axis (given by label)
        If lower and upper are equal, returns the index which exactly matches that value (if it exists)
        e.g. returns integer discrete points between two floats
        """
        path = self.fit_path(path)
        indexes = axis.find_indexes(path, self)
        search_ranges = axis.remap([lower, upper])
        original_search_ranges = axis.to_intervals([lower, upper])
        # Find the offsets for each interval in the requested range, which we will need later
        search_ranges_offset = []
        for r in original_search_ranges:
            offset = axis.offset(r)
            search_ranges_offset.append(offset)
        idx_between = self._look_up_datacube(search_ranges, search_ranges_offset, indexes, axis, method)
        # Remove duplicates even if difference of the order of the axis tolerance
        if offset is not None:
            # Note that we can only do unique if not dealing with time values
            idx_between = unique(idx_between)
        return idx_between

    def _look_up_datacube(self, search_ranges, search_ranges_offset, indexes, axis, method):
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]
            indexes_between = axis.find_indices_between([indexes], low, up, self, offset, method)
            # Now the indexes_between are values on the cyclic range so need to remap them to their original
            # values before returning them
            for j in range(len(indexes_between)):
                # if we have a special indexes between range that needs additional offset, treat it here
                if len(indexes_between[j]) == 0:
                    idx_between = idx_between
                else:
                    if indexes_between[j][0] == "need_offset":
                        print(indexes_between[j])
                        new_offset = indexes_between[j][1]
                        for k in range(2, len(indexes_between[j])):
                            if offset is None:
                                indexes_between[j][k] = indexes_between[j][k]
                            else:
                                # offset = offset + new_offset
                                offset = offset + new_offset
                                indexes_between[j][k] = round(indexes_between[j][k] + offset, int(-math.log10(axis.tol)))
                            idx_between.append(indexes_between[j][k])
                    else:
                        # do normal offset if no new offset
                        for k in range(len(indexes_between[j])):
                            print("HERE")
                            print(offset)
                            if offset is None:
                                indexes_between[j][k] = indexes_between[j][k]
                            else:
                                indexes_between[j][k] = round(indexes_between[j][k] + offset, int(-math.log10(axis.tol)))
                            idx_between.append(indexes_between[j][k])
        return idx_between

    def get_mapper(self, axis):
        """
        Get the type mapper for a subaxis of the datacube given by label
        """
        return self._axes[axis]

    def remap_path(self, path: DatacubePath):
        for key in path:
            value = path[key]
            path[key] = self._axes[key].remap([value, value])[0][0]
        return path

    @staticmethod
    def create(datacube, axis_options: dict):
        if isinstance(datacube, (xr.core.dataarray.DataArray, xr.core.dataset.Dataset)):
            from .xarray import XArrayDatacube

            xadatacube = XArrayDatacube(datacube, axis_options=axis_options)
            return xadatacube
        else:
            return datacube
