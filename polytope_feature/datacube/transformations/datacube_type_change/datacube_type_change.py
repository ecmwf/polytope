import re
from copy import deepcopy
from importlib import import_module

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
        module = import_module(
            "polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change"
        )
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.name, self.new_type))
        return transformation

    def transformation_axes_final(self):
        return [self._final_transformation.axis_name]

    def change_val_type(self, axis_name, values):
        return_idx = [self._final_transformation.transform_type(val) for val in values]
        if None in return_idx:
            return None
        return_idx.sort()
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

    def transform_type(self, value):
        try:
            return int(value)
        except ValueError:
            return None

    def make_str(self, value):
        values = []
        for val in value:
            values.append(str(val))
        return tuple(values)


class TypeChangeStrToFloat(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        try:
            return float(value)
        except ValueError:
            return None

    def make_str(self, value):
        values = []
        for val in value:
            int_val = int(val)
            if val == int_val:
                # we return a str of the integer value
                values.append(str(int_val))
            else:
                # we return a str of the float value
                values.append(str(val))
        return tuple(values)


class TypeChangeStrToTimestamp(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        try:
            return pd.Timestamp(value)
        except ValueError:
            return None

    def make_str(self, value):
        values = []
        for val in value:
            values.append(val.strftime("%Y%m%d"))
        return tuple(values)


class TypeChangeStrToTimedelta(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        try:
            hours = int(value[:2])
            mins = int(value[2:])
            return pd.Timedelta(hours=hours, minutes=mins)
        except ValueError:
            return None

    def make_str(self, value):
        values = []
        for val in value:
            hours = int(val.total_seconds() // 3600)
            mins = int((val.total_seconds() % 3600) // 60)
            values.append(f"{hours:02d}{mins:02d}")
        return tuple(values)


class TypeChangeSubHourlyTimeStepsCompact(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        if isinstance(value, int):
            return pd.Timedelta(hours=value)

        if isinstance(value, str) and value.isdigit():
            return pd.Timedelta(hours=int(value))

        if isinstance(value, str):
            # Extract hours and minutes using regex
            h_match = re.search(r"(\d+)\s*h", value)
            m_match = re.search(r"(\d+)\s*m(?:in)?", value)

            hours = int(h_match.group(1)) if h_match else 0
            minutes = int(m_match.group(1)) if m_match else 0

            return pd.Timedelta(hours=hours, minutes=minutes)

        raise ValueError(f"Unsupported timestep format: {value}")

    def make_str(self, value):
        for val in value:
            total_minutes = int(val.total_seconds() // 60)

            if total_minutes % 60 == 0:
                return f"{total_minutes // 60}"
            else:
                return f"{total_minutes}m"


class TypeChangeSubHourlyTimeSteps(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        if isinstance(value, int):
            return pd.Timedelta(hours=value)

        if isinstance(value, str) and value.isdigit():
            return pd.Timedelta(hours=int(value))

        if isinstance(value, str):
            # # Extract hours and minutes using regex
            # h_match = re.search(r"(\d+)\s*h", value)
            # m_match = re.search(r"(\d+)\s*m(?:in)?", value)

            # hours = int(h_match.group(1)) if h_match else 0
            # minutes = int(m_match.group(1)) if m_match else 0

            # return pd.Timedelta(hours=hours, minutes=minutes)
            # Extract days, hours, minutes and seconds using regex
            d_match = re.search(r"(\d+)\s*d", value)
            h_match = re.search(r"(\d+)\s*h", value)
            m_match = re.search(r"(\d+)\s*m(?:in)?", value)
            s_match = re.search(r"(\d+)\s*s(?:ec)?", value)

            days = int(d_match.group(1)) if d_match else 0
            hours = int(h_match.group(1)) if h_match else 0
            minutes = int(m_match.group(1)) if m_match else 0
            seconds = int(s_match.group(1)) if s_match else 0

            return pd.Timedelta(
                days=days, hours=hours, minutes=minutes, seconds=seconds
            )

        raise ValueError(f"Unsupported timestep format: {value}")

    def make_str(self, value):
        for val in value:
            # total_minutes = int(val.total_seconds() // 60)
            # hours, minutes = divmod(total_minutes, 60)

            # if hours == 0 and minutes == 0:
            #     return "0"
            # elif hours == 0:
            #     return f"{minutes}m"
            # elif minutes == 0:
            #     return f"{hours}h"
            # else:
            #     return f"{hours}h{minutes}m"
            total_seconds = int(val.total_seconds())
            days, rem = divmod(total_seconds, 86400)
            hours, rem = divmod(rem, 3600)
            minutes, seconds = divmod(rem, 60)

            if days == 0 and hours == 0 and minutes == 0 and seconds == 0:
                return "0"
            # Prefer compact forms when possible to remain backwards compatible
            if days > 0:
                parts = [f"{days}d"]
                if hours > 0:
                    parts.append(f"{hours}h")
                if minutes > 0:
                    parts.append(f"{minutes}m")
                if seconds > 0:
                    parts.append(f"{seconds}s")
                return "".join(parts)
            if hours == 0:
                if minutes == 0:
                    return f"{seconds}s"
                if seconds == 0:
                    return f"{minutes}m"
                return f"{minutes}m{seconds}s"
            # hours > 0
            if minutes == 0 and seconds == 0:
                return f"{hours}"
            if seconds == 0:
                return f"{hours}h{minutes}m"
            return f"{hours}h{minutes}m{seconds}s"


_type_to_datacube_type_change_lookup = {
    "int": "TypeChangeStrToInt",
    "date": "TypeChangeStrToTimestamp",
    "time": "TypeChangeStrToTimedelta",
    "float": "TypeChangeStrToFloat",
    "subhourly_step_compact": "TypeChangeSubHourlyTimeStepsCompact",
    "subhourly_step": "TypeChangeSubHourlyTimeSteps",
}
