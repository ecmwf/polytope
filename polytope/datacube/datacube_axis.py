import bisect
from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, List

import numpy as np
import pandas as pd

from .transformations.datacube_cyclic.datacube_cyclic import DatacubeAxisCyclic
from .transformations.datacube_mappers.datacube_mappers import DatacubeMapper
from .transformations.datacube_merger.datacube_merger import DatacubeAxisMerger
from .transformations.datacube_reverse.datacube_reverse import DatacubeAxisReverse
from .transformations.datacube_type_change.datacube_type_change import (
    DatacubeAxisTypeChange,
)


class DatacubeAxis(ABC):
    is_cyclic = False
    has_mapper = False
    has_merger = False
    reorder = False
    type_change = False

    def order_tranformations(self):
        self.transformations = sorted(self.transformations, key=lambda x: transformations_order[type(x)])

    def give_transformations_parents(self):
        for i, transform in enumerate(self.transformations[1:]):
            transform.parent = self.transformations[i - 1]

    # Convert from user-provided value to CONTINUOUS type (e.g. float, pd.timestamp)
    @abstractmethod
    def parse(self, value: Any) -> Any:
        pass

    # Convert from CONTINUOUS type to FLOAT
    @abstractmethod
    def to_float(self, value: Any) -> float:
        pass

    # Convert from FLOAT type to CONTINUOUS type
    @abstractmethod
    def from_float(self, value: float) -> Any:
        pass

    def serialize(self, value: Any) -> Any:
        pass

    def to_intervals(self, range):
        intervals = [range]
        for transformation in self.transformations[::-1]:
            intervals = transformation.to_intervals(range, intervals, self)
        return intervals

    def remap(self, range: List) -> Any:
        ranges = [range]
        for transformation in self.transformations[::-1]:
            ranges = transformation.remap(range, ranges, self)
        return ranges

    def unmap_to_datacube(self, path, unmapped_path):
        return (path, unmapped_path)

    def find_standard_indexes(self, path, datacube):
        unmapped_path = {}
        path_copy = deepcopy(path)
        for key in path_copy:
            axis = datacube._axes[key]
            (path, unmapped_path) = axis.unmap_to_datacube(path, unmapped_path)
        subarray = datacube.select(path, unmapped_path)
        return datacube.datacube_natural_indexes(self, subarray)

    def find_indexes(self, path, datacube):
        indexes = self.find_standard_indexes(path, datacube)
        for transformation in self.transformations[::-1]:
            indexes = transformation.find_modified_indexes(indexes, path, datacube, self)
        return indexes

    def offset(self, value):
        offset = 0
        for transformation in self.transformations[::-1]:
            offset = transformation.offset(value, self, offset)
        return offset

    def unmap_path_key(self, key_value_path, leaf_path, unwanted_path):
        for transformation in self.transformations[::-1]:
            (key_value_path, leaf_path, unwanted_path) = transformation.unmap_path_key(
                key_value_path, leaf_path, unwanted_path, self
            )
        return (key_value_path, leaf_path, unwanted_path)

    def unmap_tree_node(self, node, unwanted_path):
        for transformation in self.transformations[::-1]:
            (node, unwanted_path) = transformation.unmap_tree_node(node, unwanted_path)
        return (node, unwanted_path)

    def _remap_val_to_axis_range(self, value):
        for transformation in self.transformations[::-1]:
            value = transformation._remap_val_to_axis_range(value, self)
        return value

    def find_standard_indices_between(self, indexes, low, up, datacube, method=None):
        indexes_between_ranges = []

        if self.name in datacube.complete_axes and self.name not in datacube.transformed_axes:
            # Find the range of indexes between lower and upper
            # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
            # Assumes the indexes are already sorted (could sort to be sure) and monotonically increasing
            if method == "surrounding" or method == "nearest":
                start = indexes.searchsorted(low, "left")
                end = indexes.searchsorted(up, "right")
                start = max(start - 1, 0)
                end = min(end + 1, len(indexes))
                indexes_between = indexes[start:end].to_list()
                indexes_between_ranges.extend(indexes_between)
            else:
                start = indexes.searchsorted(low, "left")
                end = indexes.searchsorted(up, "right")
                indexes_between = indexes[start:end].to_list()
                indexes_between_ranges.extend(indexes_between)
        else:
            if method == "surrounding" or method == "nearest":
                start = bisect.bisect_left(indexes, low)
                end = bisect.bisect_right(indexes, up)
                start = max(start - 1, 0)
                end = min(end + 1, len(indexes))
                indexes_between = indexes[start:end]
                indexes_between_ranges.extend(indexes_between)
            else:
                lower_idx = bisect.bisect_left(indexes, low)
                upper_idx = bisect.bisect_right(indexes, up)
                indexes_between = indexes[lower_idx:upper_idx]
                indexes_between_ranges.extend(indexes_between)
        return indexes_between_ranges

    def find_indices_between(self, indexes_ranges, low, up, datacube, method=None):
        indexes_between_ranges = self.find_standard_indices_between(indexes_ranges, low, up, datacube, method)
        for transformation in self.transformations[::-1]:
            indexes_between_ranges = transformation.find_indices_between(
                indexes_ranges, low, up, datacube, method, indexes_between_ranges, self
            )
        return indexes_between_ranges

    @staticmethod
    def create_standard(name, values, datacube):
        values = np.array(values)
        DatacubeAxis.check_axis_type(name, values)
        if datacube._axes is None:
            datacube._axes = {name: deepcopy(_type_to_axis_lookup[values.dtype.type])}
        else:
            datacube._axes[name] = deepcopy(_type_to_axis_lookup[values.dtype.type])
        datacube._axes[name].name = name
        datacube.axis_counter += 1

    @staticmethod
    def check_axis_type(name, values):
        # NOTE: The values here need to be a numpy array which has a dtype attribute
        if values.dtype.type not in _type_to_axis_lookup:
            raise ValueError(f"Could not create a mapper for index type {values.dtype.type} for axis {name}")


transformations_order = [
    DatacubeAxisMerger,
    DatacubeAxisReverse,
    DatacubeAxisCyclic,
    DatacubeMapper,
    DatacubeAxisTypeChange,
]
transformations_order = {key: i for i, key in enumerate(transformations_order)}


class IntDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        # TODO: Maybe here, store transformations as a dico instead
        self.transformations = []
        self.type = 0
        self.can_round = True

    def parse(self, value: Any) -> Any:
        return float(value)

    def to_float(self, value):
        return float(value)

    def from_float(self, value):
        return float(value)

    def serialize(self, value):
        return value


class FloatDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = 0.0
        self.can_round = True

    def parse(self, value: Any) -> Any:
        return float(value)

    def to_float(self, value):
        return float(value)

    def from_float(self, value):
        return float(value)

    def serialize(self, value):
        return value


class PandasTimestampDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = pd.Timestamp("2000-01-01T00:00:00")
        self.can_round = False

    def parse(self, value: Any) -> Any:
        if isinstance(value, np.str_):
            value = str(value)
        return pd.Timestamp(value)

    def to_float(self, value: pd.Timestamp):
        if isinstance(value, np.datetime64):
            return float((value - np.datetime64("1970-01-01T00:00:00")).astype("int"))
        else:
            return float(value.value / 10**9)

    def from_float(self, value):
        return pd.Timestamp(int(value), unit="s")

    def serialize(self, value):
        return str(value)

    def offset(self, value):
        return None


class PandasTimedeltaDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = np.timedelta64(0, "s")
        self.can_round = False

    def parse(self, value: Any) -> Any:
        if isinstance(value, np.str_):
            value = str(value)
        return pd.Timedelta(value)

    def to_float(self, value: pd.Timedelta):
        if isinstance(value, np.timedelta64):
            return value.astype("timedelta64[s]").astype(int)
        else:
            return float(value.value / 10**9)

    def from_float(self, value):
        return pd.Timedelta(int(value), unit="s")

    def serialize(self, value):
        return str(value)

    def offset(self, value):
        return None


class UnsliceableDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = float("NaN")
        self.range = None
        self.transformations = []
        self.can_round = False

    def parse(self, value: Any) -> Any:
        return value

    def to_float(self, value: pd.Timedelta):
        raise TypeError("Tried to slice unsliceable axis")

    def from_float(self, value):
        raise TypeError("Tried to slice unsliceable axis")

    def serialize(self, value):
        raise TypeError("Tried to slice unsliceable axis")


_type_to_axis_lookup = {
    pd.Int64Dtype: IntDatacubeAxis(),
    pd.Timestamp: PandasTimestampDatacubeAxis(),
    np.int64: IntDatacubeAxis(),
    np.datetime64: PandasTimestampDatacubeAxis(),
    np.timedelta64: PandasTimedeltaDatacubeAxis(),
    np.float64: FloatDatacubeAxis(),
    np.float32: FloatDatacubeAxis(),
    np.int32: IntDatacubeAxis(),
    np.str_: UnsliceableDatacubeAxis(),
    str: UnsliceableDatacubeAxis(),
    np.object_: UnsliceableDatacubeAxis(),
}
