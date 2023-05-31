import math
import sys
from copy import deepcopy

import numpy as np
import pandas as pd
import xarray as xr

from ..utility.combinatorics import unique, validate_axes
from .datacube import Datacube, DatacubePath, DatacubeRequestTree
from .datacube_axis import (
    FloatAxis,
    IntAxis,
    PandasTimedeltaAxis,
    PandasTimestampAxis,
    UnsliceableaAxis,
)

_mappings = {
    pd.Int64Dtype: IntAxis(),
    pd.Timestamp: PandasTimestampAxis(),
    np.int64: IntAxis(),
    np.datetime64: PandasTimestampAxis(),
    np.timedelta64: PandasTimedeltaAxis(),
    np.float64: FloatAxis(),
    np.float32: FloatAxis(),
    np.str_: UnsliceableaAxis(),
    str: UnsliceableaAxis(),
}


class XArrayDatacube(Datacube):

    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def __init__(self, dataarray: xr.DataArray, options={}):
        self.options = options
        self.mappers = {}
        for name, values in dataarray.coords.variables.items():
            if name in dataarray.dims:
                dataarray = dataarray.sortby(name)
                if values.dtype.type not in _mappings:
                    raise ValueError(f"Could not create a mapper for index type {values.dtype.type} for axis {name}")
                if name in self.options.keys():
                    # The options argument here is supposed to be a nested dictionary
                    # like {"latitude":{"Cyclic":range}, ...}
                    # TODO: would it be faster if instead we just add an option when it's cyclic and then evaluate to
                    # true or false? Maybe there is a better/faster way of accessing options
                    if "Cyclic" in self.options[name].keys():
                        value_type = values.dtype.type
                        axes_type_str = type(_mappings[value_type]).__name__
                        axes_type_str += "Cyclic"
                        cyclic_axis_type = deepcopy(
                            getattr(sys.modules["polytope.datacube.datacube_axis"], axes_type_str)()
                        )
                        self.mappers[name] = cyclic_axis_type
                        self.mappers[name].name = name
                        self.mappers[name].range = self.options[name]["Cyclic"]
                else:
                    self.mappers[name] = deepcopy(_mappings[values.dtype.type])
                    self.mappers[name].name = name

            else:  # drop non-necessary coordinates which we don't slice on
                dataarray = dataarray.reset_coords(names=name, drop=True)

        self.dataarray = dataarray

    def get(self, requests: DatacubeRequestTree):
        for r in requests.leaves:
            path = r.flatten()
            path = self.remap_path(path)
            # TODO: Here, once we flatten the path, we want to remap the values on the axis to fit the datacube...
            if len(path.items()) == len(self.dataarray.dims):
                subxarray = self.dataarray.sel(path, method="nearest")
                data_variables = subxarray.data_vars
                result_tuples = [(key, value) for key, value in data_variables.items()]
                r.result = dict(result_tuples)
            else:
                r.remove_branch()

    def get_mapper(self, label):
        return self.mappers[label]

    def remap_path(self, path: DatacubePath):
        for key in path:
            value = path[key]
            path[key] = self.mappers[key].remap_val_to_axis_range(value)
        return path

    def get_indices(self, path: DatacubePath, axis, lower, upper):
        path = self.remap_path(path)
        # Open a view on the subset identified by the path
        subarray = self.dataarray.sel(path, method="nearest")

        # Get the indexes of the axis we want to query
        # XArray does not support branching, so no need to use label, we just take the next axis
        # TODO: should assert that the label == next axis

        indexes = next(iter(subarray.xindexes.values())).to_pandas_index()

        # Here, we do a cyclic remapping so we look up on the right existing values in the cyclic range on the datacube
        idx_between = []
        search_ranges = axis.remap([lower, upper])
        original_search_ranges = axis.to_intervals([lower, upper])

        # Find the offsets for each interval in the requested range, which we will need later
        search_ranges_offset = []
        for r in original_search_ranges:
            offset = axis.offset(r)
            search_ranges_offset.append(offset)

        # Look up the values in the datacube for each cyclic interval range
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]
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
