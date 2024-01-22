import bisect
from copy import deepcopy
from importlib import import_module

from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisTypeChange(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, type_options):
        self.name = name
        self.transformation_options = type_options
        self.new_type = type_options
        self._final_transformation = self.generate_final_transformation()

    def generate_final_transformation(self):
        map_type = _type_to_datacube_type_change_lookup[self.new_type]
        module = import_module("polytope.datacube.transformations.datacube_type_change")
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.name, self.new_type))
        return transformation

    def transformation_axes_final(self):
        return [self._final_transformation.axis_name]

    def change_val_type(self, axis_name, values):
        return_idx = [self._final_transformation.transform_type(val) for val in values]
        return_idx.sort()
        return return_idx

    def make_str(self, value):
        return self._final_transformation.make_str(value)

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return []


class TypeChangeStrToInt(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        return int(value)

    def make_str(self, value):
        return str(value)


_type_to_datacube_type_change_lookup = {"int": "TypeChangeStrToInt"}


def type_change(cls):
    if cls.type_change:
        old_find_indexes = cls.find_indexes

        def find_indexes(path, datacube):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        original_vals = old_find_indexes(path, datacube)
                        return transformation.change_val_type(cls.name, original_vals)

        old_unmap_path_key = cls.unmap_path_key

        def unmap_path_key(key_value_path, leaf_path, unwanted_path):
            key_value_path, leaf_path, unwanted_path = old_unmap_path_key(key_value_path, leaf_path, unwanted_path)
            value = key_value_path[cls.name]
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    if cls.name == transform.name:
                        unchanged_val = transform.make_str(value)
                        key_value_path[cls.name] = unchanged_val
            return (key_value_path, leaf_path, unwanted_path)

        def unmap_to_datacube(path, unmapped_path):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        changed_val = path.get(cls.name, None)
                        unchanged_val = transformation.make_str(changed_val)
                        if cls.name in path:
                            path.pop(cls.name, None)
                            unmapped_path[cls.name] = unchanged_val
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        for indexes in index_ranges:
                            if method == "surrounding":
                                start = indexes.index(low)
                                end = indexes.index(up)
                                start = max(start - 1, 0)
                                end = min(end + 1, len(indexes))
                                indexes_between = indexes[start:end]
                                indexes_between_ranges.append(indexes_between)
                            else:
                                lower_idx = bisect.bisect_left(indexes, low)
                                upper_idx = bisect.bisect_right(indexes, up)
                                indexes_between = indexes[lower_idx:upper_idx]
                                indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.find_indices_between = find_indices_between
        cls.unmap_path_key = unmap_path_key

    return cls
