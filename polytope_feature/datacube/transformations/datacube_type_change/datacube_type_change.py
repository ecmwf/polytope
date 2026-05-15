import re
from copy import deepcopy
from importlib import import_module

import pandas as pd

from ..datacube_transformations import DatacubeAxisTransformation

_STEP_COMPONENT_PATTERN = re.compile(
    r"^\s*(?:(?P<days>\d+)\s*d(?:ays?)?\s*)?"
    r"(?:(?P<hours>\d+)\s*h(?:ours?)?\s*)?"
    r"(?:(?P<minutes>\d+)\s*m(?:in(?:utes?)?)?\s*)?"
    r"(?:(?P<seconds>\d+)\s*s(?:ec(?:onds?)?)?\s*)?$"
)


def parse_step_timedelta(value):
    if isinstance(value, pd.Timedelta):
        return value

    if isinstance(value, int):
        return pd.Timedelta(hours=value)

    if not isinstance(value, str):
        raise ValueError(f"Unsupported timestep format: {value}")

    normalized = value.strip()
    if normalized.isdigit():
        return pd.Timedelta(hours=int(normalized))

    match = _STEP_COMPONENT_PATTERN.fullmatch(normalized)
    if match and any(component is not None for component in match.groupdict().values()):
        return pd.Timedelta(
            days=int(match.group("days") or 0),
            hours=int(match.group("hours") or 0),
            minutes=int(match.group("minutes") or 0),
            seconds=int(match.group("seconds") or 0),
        )

    raise ValueError(f"Unsupported timestep format: {value}")


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
        return_idx = [self._final_transformation.transform_type(val) for val in values]
        if None in return_idx:
            return None
        return_idx.sort(key=lambda x: (isinstance(x, str), x))
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
        if isinstance(value, str) and "-" in value:
            return value.strip()
        return parse_step_timedelta(value)

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
        if isinstance(value, str) and "-" in value:
            return value.strip()
        return parse_step_timedelta(value)

    def make_str(self, value):
        return_vals = []
        for val in value:
            if isinstance(val, str):
                return_vals.append(val)
                continue
            total_seconds = int(val.total_seconds())
            hours, rem = divmod(total_seconds, 3600)
            minutes, seconds = divmod(rem, 60)

            if hours == 0 and minutes == 0 and seconds == 0:
                return_vals.append("0")
            # Prefer compact forms when possible to remain backwards compatible
            elif hours > 0:
                parts = [f"{hours}h"]
                if minutes == 0 and seconds == 0:
                    return_vals.append(f"{hours}")
                    continue
                if minutes > 0:
                    parts.append(f"{minutes}m")
                if seconds > 0:
                    parts.append(f"{seconds}s")
                return_vals.append("".join(parts))
            elif hours == 0:
                if minutes == 0:
                    return_vals.append(f"{seconds}s")
                elif seconds == 0:
                    return_vals.append(f"{minutes}m")
                else:
                    return_vals.append(f"{minutes}m{seconds}s")
        return list(dict.fromkeys(return_vals))


_type_to_datacube_type_change_lookup = {
    "int": "TypeChangeStrToInt",
    "date": "TypeChangeStrToTimestamp",
    "time": "TypeChangeStrToTimedelta",
    "float": "TypeChangeStrToFloat",
    "subhourly_step_compact": "TypeChangeSubHourlyTimeStepsCompact",
    "subhourly_step": "TypeChangeSubHourlyTimeSteps",
}
