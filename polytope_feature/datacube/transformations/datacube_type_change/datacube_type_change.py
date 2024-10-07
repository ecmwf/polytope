from copy import deepcopy
from importlib import import_module

from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisTypeChange(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, type_options):
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
        return int(value)

    def make_str(self, value):
        values = []
        for val in value:
            values.append(str(val))
        return tuple(values)


_type_to_datacube_type_change_lookup = {"int": "TypeChangeStrToInt"}
