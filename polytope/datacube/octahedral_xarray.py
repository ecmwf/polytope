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

_mappings = {
    pd.Int64Dtype: IntAxis(),
    pd.Timestamp: PandasTimestampAxis(),
    np.int64: IntAxis(),
    np.datetime64: PandasTimestampAxis(),
    np.timedelta64: PandasTimedeltaAxis(),
    np.float64: FloatAxis(),
    np.str_: UnsliceableaAxis(),
    str: UnsliceableaAxis(),
}


class OctahedralXArrayDatacube(Datacube):
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

    def __init__(self, dataarray: xr.DataArray, options={}):
        self.options = options
        self.mappers = {}
        for name, values in dataarray.coords.variables.items():
            if values.data.size != 1:
                self._set_mapper(values, name)
            else:  # drop non-necessary coordinates which we don't slice on
                dataarray = dataarray.reset_coords(names=name, drop=True)

        self.dataarray = dataarray

    def get(self, requests: IndexTree):
        for r in requests.leaves:
            path = r.flatten()
            path = self.remap_path(path)
            len_coords = 0
            for name, values in self.dataarray.coords.variables.items():
                if values.data.size != 1:
                    len_coords += 1
            if len(path.items()) == len_coords:
                lat_val = path["latitude"]
                lon_val = path["longitude"]
                path.pop("longitude", None)
                path.pop("latitude", None)
                subxarray = self.dataarray.sel(path, method="nearest")
                # need to remap the lat, lon in path to dataarray index
                lat_idx, lon_idx = latlon_val_to_idx(lat_val, lon_val)
                octa_idx = latlon_idx_to_octa_idx(lat_idx, lon_idx)
                subxarray = subxarray.isel(values=octa_idx)
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

    def _look_up_datacube(self, search_ranges, search_ranges_offset, indexes, axis):
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]

            if axis.name == "latitude" or axis.name == "longitude":
                indexes_between = [i for i in indexes if low <= i <= up]
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
        # Open a view on the subset identified by the path
        lat_val = path.get("latitude", None)
        path.pop("longitude", None)
        path.pop("latitude", None)
        subarray = self.dataarray.sel(path, method="nearest")

        # Get the indexes of the axis we want to query
        # XArray does not support branching, so no need to use label, we just take the next axis
        if axis.name == "latitude":
            indexes = self.lat_val_available()
        elif axis.name == "longitude":
            indexes = self.lon_val_available(lat_val)
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
        idx_between = self._look_up_datacube(search_ranges, search_ranges_offset, indexes, axis)

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

    def lat_val_available(self):
        lat_spacing = 90 / 1280
        lat_start = 0.035149384215604956
        return_lat = [lat_start + i * lat_spacing - 90 for i in range(1280 * 2)]
        return return_lat

    def lon_val_available(self, lat):
        lat_spacing = 90 / 1280
        lat_start = 0.035149384215604956
        if lat_start <= lat < 90:
            lat_idx = 1280 - ((lat - lat_start) / lat_spacing)
        else:
            lat_idx = (lat + 90 - lat_start) / lat_spacing
        num_points_on_lon = 4 * lat_idx + 16
        lon_spacing = 360 / num_points_on_lon
        lon_start = 0
        return_lon = [lon_start + i * lon_spacing for i in range(int(num_points_on_lon))]
        return return_lon


def latlon_idx_to_octa_idx(lat_idx, lon_idx):
    if lat_idx <= 1280:
        # we are at lat >0
        # lat_idx 0 is lat=90
        octa_idx = 0
        if lat_idx == 1:
            octa_idx = lon_idx
        else:
            for i in range(lat_idx - 1):
                octa_idx += 16 + 4 * (i)
            octa_idx = int(octa_idx + lon_idx)
    else:
        # we are at lat <0
        octa_idx = int(6599680 / 2)
        lat_idx = lat_idx - 1280
        if lat_idx == 1:
            octa_idx += lon_idx
        else:
            for i in range(lat_idx - 1):
                octa_idx += 16 + 4 * (1280 - i - 1)
            octa_idx = octa_idx + lon_idx
            if lat_idx == 1280:
                lat_idx -= 16
    return octa_idx


def latlon_val_to_idx(lat, lon):
    lat_spacing = 90 / 1280
    lat_start = 0.03515625
    if lat_start <= lat <= 90:
        # if we are at lat=90, the latitude line index is 0
        lat_idx = 1280 - ((lat - lat_start) / lat_spacing)
    else:
        # if we are at lat=-90, the latitude line index is 2560
        lat_idx = 1280 - ((lat - lat_start) / lat_spacing)
    num_points_on_lon = 4 * lat_idx + 16
    lon_spacing = 360 / num_points_on_lon
    lon_start = 0
    lon_idx = (lon - lon_start) / lon_spacing

    return (int(lat_idx), lon_idx)
