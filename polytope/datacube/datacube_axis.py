from abc import ABC, abstractmethod
from copy import deepcopy
from typing import Any, List

import numpy as np
import pandas as pd

from .transformations.datacube_cyclic import cyclic
from .transformations.datacube_mappers import mapper
from .transformations.datacube_merger import merge
from .transformations.datacube_reverse import reverse
from .transformations.datacube_type_change import type_change


class DatacubeAxis(ABC):
    is_cyclic = False
    has_mapper = False
    has_merger = False
    reorder = False
    type_change = False

    def update_axis(self):
        if self.is_cyclic:
            self = cyclic(self)
        return self

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
        return [range]

    def remap(self, range: List) -> Any:
        return [range]

    def unmap_to_datacube(self, path, unmapped_path):
        return (path, unmapped_path)

    def find_indexes(self, path, datacube):
        unmapped_path = {}
        path_copy = deepcopy(path)
        for key in path_copy:
            axis = datacube._axes[key]
            (path, unmapped_path) = axis.unmap_to_datacube(path, unmapped_path)
        subarray = datacube.select(path, unmapped_path)
        return datacube.datacube_natural_indexes(self, subarray)

    def offset(self, value):
        return 0

    def unmap_path_key(self, key_value_path, leaf_path, unwanted_path):
        return (key_value_path, leaf_path, unwanted_path)

    def find_indices_between(self, index_ranges, low, up, datacube, method=None):
        # TODO: add method for snappping
        indexes_between_ranges = []
        for indexes in index_ranges:
            if self.name in datacube.complete_axes:
                # Find the range of indexes between lower and upper
                # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
                # Assumes the indexes are already sorted (could sort to be sure) and monotonically increasing
                if method == "surrounding":
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    start = max(start - 1, 0)
                    end = min(end + 1, len(indexes))
                    indexes_between = indexes[start:end].to_list()
                    indexes_between_ranges.append(indexes_between)
                else:
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    indexes_between = indexes[start:end].to_list()
                    indexes_between_ranges.append(indexes_between)
            else:
                if method == "surrounding":
                    start = indexes.index(low)
                    end = indexes.index(up)
                    start = max(start - 1, 0)
                    end = min(end + 1, len(indexes))
                    indexes_between = indexes[start:end]
                    indexes_between_ranges.append(indexes_between)
                else:
                    indexes_between = [i for i in indexes if low <= i <= up]
                    indexes_between_ranges.append(indexes_between)
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


@reverse
@cyclic
@mapper
@type_change
class IntDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = 0

    def parse(self, value: Any) -> Any:
        return float(value)

    def to_float(self, value):
        return float(value)

    def from_float(self, value):
        return float(value)

    def serialize(self, value):
        return value


@reverse
@cyclic
@mapper
@type_change
class FloatDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = 0.0

    def parse(self, value: Any) -> Any:
        return float(value)

    def to_float(self, value):
        return float(value)

    def from_float(self, value):
        return float(value)

    def serialize(self, value):
        return value


@merge
class PandasTimestampDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = pd.Timestamp("2000-01-01T00:00:00")

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


@merge
class PandasTimedeltaDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = 1e-12
        self.range = None
        self.transformations = []
        self.type = np.timedelta64(0, "s")

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


@type_change
class UnsliceableDatacubeAxis(DatacubeAxis):
    def __init__(self):
        self.name = None
        self.tol = float("NaN")
        self.range = None
        self.transformations = []

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
    np.str_: UnsliceableDatacubeAxis(),
    str: UnsliceableDatacubeAxis(),
    np.object_: UnsliceableDatacubeAxis(),
}
