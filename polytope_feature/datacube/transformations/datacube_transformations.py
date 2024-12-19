from abc import ABC, abstractmethod
from copy import deepcopy
from importlib import import_module


class DatacubeAxisTransformation(ABC):
    def __init__(self):
        self.parent = None

    @staticmethod
    def create_transform(name, transformation_type_key, transformation_options):
        transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]
        transformation_file_name = _type_to_transformation_file_lookup[transformation_type_key]
        file_name = ".datacube_" + transformation_file_name
        module = import_module("polytope_feature.datacube.transformations" + file_name + file_name)
        constructor = getattr(module, transformation_type)
        transformation_type_option = transformation_options
        new_transformation = deepcopy(constructor(name, transformation_type_option))

        new_transformation.name = name
        return new_transformation

    @staticmethod
    def get_final_axes(name, transformation_type_key, transformation_options):
        new_transformation = DatacubeAxisTransformation.create_transform(
            name, transformation_type_key, transformation_options
        )
        transformation_axis_names = new_transformation.transformation_axes_final()
        return transformation_axis_names

    def name(self):
        pass

    def transformation_options(self):
        pass

    @abstractmethod
    def generate_final_transformation(self):
        pass

    @abstractmethod
    def transformation_axes_final(self):
        pass

    @abstractmethod
    def change_val_type(self, axis_name, values):
        pass

    def find_modified_indexes(self, indexes, path, datacube, axis):
        return indexes

    def unmap_path_key(self, key_value_path, leaf_path, unwanted_path, axis):
        return (key_value_path, leaf_path, unwanted_path)

    def unmap_tree_node(self, node, unwanted_path):
        return (node, unwanted_path)

    def find_indices_between(self, indexes_ranges, low, up, datacube, method, indexes_between_ranges, axis):
        return indexes_between_ranges

    def _remap_val_to_axis_range(self, value, axis):
        return value

    def offset(self, range, axis, offset):
        return offset

    def remap(self, range, ranges, axis):
        return ranges

    def to_intervals(self, range, intervals, axis):
        return intervals


_type_to_datacube_transformation_lookup = {
    "mapper": "DatacubeMapper",
    "cyclic": "DatacubeAxisCyclic",
    "merge": "DatacubeAxisMerger",
    "reverse": "DatacubeAxisReverse",
    "type_change": "DatacubeAxisTypeChange",
}

_type_to_transformation_file_lookup = {
    "mapper": "mappers",
    "cyclic": "cyclic",
    "merge": "merger",
    "reverse": "reverse",
    "type_change": "type_change",
}

has_transform = {
    "mapper": "has_mapper",
    "cyclic": "is_cyclic",
    "merge": "has_merger",
    "reverse": "reorder",
    "type_change": "type_change",
}
