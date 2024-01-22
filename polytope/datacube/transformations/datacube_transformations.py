from abc import ABC, abstractmethod
from copy import deepcopy
from importlib import import_module


class DatacubeAxisTransformation(ABC):
    @staticmethod
    def create_transform(name, transformation_type_key, transformation_options):
        transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]
        transformation_file_name = _type_to_transformation_file_lookup[transformation_type_key]

        module = import_module("polytope.datacube.transformations.datacube_" + transformation_file_name)
        constructor = getattr(module, transformation_type)
        transformation_type_option = transformation_options[transformation_type_key]
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


_type_to_datacube_transformation_lookup = {
    "mapper": "DatacubeMapper",
    "cyclic": "DatacubeAxisCyclic",
    "merge": "DatacubeAxisMerger",
    "reverse": "DatacubeAxisReverse",
    "type_change": "DatacubeAxisTypeChange",
    "null": "DatacubeNullTransformation",
}

_type_to_transformation_file_lookup = {
    "mapper": "mappers.datacube_mappers",
    "cyclic": "cyclic.datacube_cyclic",
    "merge": "merger",
    "reverse": "reverse",
    "type_change": "type_change",
    "null": "null_transformation",
}

has_transform = {
    "mapper": "has_mapper",
    "cyclic": "is_cyclic",
    "merge": "has_merger",
    "reverse": "reorder",
    "type_change": "type_change",
    "null": "null",
}
