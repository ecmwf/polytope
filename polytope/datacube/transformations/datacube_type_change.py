from copy import deepcopy
from importlib import import_module

from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisTypeChange(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, type_options):
        self.name = name
        self.transformation_options = type_options
        self.new_type = type_options

    def generate_final_transformation(self):
        map_type = _type_to_datacube_type_change_lookup[self.new_type]
        module = import_module("polytope.datacube.transformations.datacube_type_change")
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.name, self.new_type))
        return transformation

    def transformation_axes_final(self):
        final_transformation = self.generate_final_transformation()
        return [final_transformation.axis_name]

    def change_val_type(self, axis_name, values):
        transformation = self.generate_final_transformation()
        return [transformation.transform_type(val) for val in values]

    def make_str(self, value):
        transformation = self.generate_final_transformation()
        return transformation.make_str(value)

    def blocked_axes(self):
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
