from copy import deepcopy
from importlib import import_module

import numpy as np
import pandas as pd

from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisTypeChange(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, type_options, datacube=None):
        self.name = name
        self.transformation_options = type_options
        self.new_type = type_options.type
        self._final_transformation = self.generate_final_transformation()

    def generate_final_transformation(self):
        map_type = _type_to_datacube_type_change_lookup[self.new_type]
        module = import_module("polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change")
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.name, self.new_type))
        return transformation

    def transformation_axes_final(self):
        return [self._final_transformation.axis_name]

    def change_val_type(self, axis_name, values):
        return_idx = self._final_transformation.transform_type(values)
        if np.any(return_idx is None):
            return None
        return return_idx

    def make_str(self, value):
        return self._final_transformation.make_str(value)

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return []

    def find_modified_indexes(self, indexes, path, datacube, axis):
        if axis.name == self.name:
            return self.change_val_type(axis.name, indexes)

    def unmap_path_key(self, key_value_path, leaf_path, unwanted_path, axis):
        value = key_value_path[axis.name]
        if axis.name == self.name:
            unchanged_val = self.make_str(value)
            key_value_path[axis.name] = unchanged_val
        return (key_value_path, leaf_path, unwanted_path)

    def unmap_tree_node(self, node, unwanted_path):
        if node.axis.name == self.name:
            new_node_vals = self.make_str(node.values)
            node.values = new_node_vals
        return (node, unwanted_path)


class TypeChangeStrToInt(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, values):
        values_array = np.array(values, dtype='object')
        vectorized_int = np.vectorize(lambda x: int(x) if isinstance(
            x, (int, float, str)) and str(x).isdigit() else None)
        return_vals = vectorized_int(values_array)
        return_vals.sort()
        return return_vals

    def make_str(self, value):
        values = np.asarray(value).astype(str)
        return tuple(values)


class TypeChangeStrToTimestamp(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        return_vals = pd.to_datetime(value, errors='coerce')
        return_vals.sort_values()
        return return_vals

    def make_str(self, value):
        dt_series = pd.Series(value)
        formatted = dt_series.dt.strftime("%Y%m%d")
        return tuple(formatted)


class TypeChangeStrToTimedelta(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        values_series = pd.Series(value)
        hours = values_series.str[:2].astype(int, errors='ignore')
        mins = values_series.str[2:].astype(int, errors='ignore')
        invalid_mask = (hours.isna()) | (mins.isna())
        result = pd.to_timedelta(hours, unit='h') + pd.to_timedelta(mins, unit='m')
        result[invalid_mask] = pd.NaT
        result.sort_values()
        return result

    def make_str(self, value):
        val_array = np.asarray(value).astype('timedelta64[s]')
        total_seconds = val_array.astype('int')
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        formatted = np.char.add(
            np.char.zfill(hours.astype(str), 2),
            np.char.zfill(minutes.astype(str), 2)
        )
        return tuple(formatted)


_type_to_datacube_type_change_lookup = {
    "int": "TypeChangeStrToInt",
    "date": "TypeChangeStrToTimestamp",
    "time": "TypeChangeStrToTimedelta",
}
