from copy import deepcopy
from importlib import import_module

from ..backends.datacube import configure_datacube_axis
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

    def apply_transformation(self, name, datacube, values):
        transformation = self.generate_final_transformation()
        axis_options = deepcopy(datacube.axis_options[name]["transformation"])
        axis_options.pop("type_change")
        # Update the nested dictionary with the modified axis option for our axis
        new_datacube_axis_options = deepcopy(datacube.axis_options)
        # if we have no transformations left, then empty the transformation dico
        if axis_options == {}:
            new_datacube_axis_options[name] = {}
        else:
            new_datacube_axis_options[name]["transformation"] = axis_options
        values = [transformation.transform_type(values[0])]  # only need 1 value to determine type in datacube config
        configure_datacube_axis(new_datacube_axis_options[name], name, values, datacube)

    def _find_transformed_indices_between(self, axis, datacube, indexes, low, up, first_val, offset):
        # NOTE: needs to be in new type
        if axis.name == self.name:
            transformation = self.generate_final_transformation()
            indexes_between = [
                transformation.transform_type(i) for i in indexes if low <= transformation.transform_type(i) <= up
            ]
            # indexes_between = []
        else:
            indexes_between = datacube._find_indexes_between(axis, indexes, low, up)
        return (offset, indexes_between)

    def _adjust_path(self, path, considered_axes=[], unmap_path={}, changed_type_path={}):
        # NOTE: used to access values, so path for the axis needs to be replaced to original type index
        axis_new_val = path.get(self.name, None)
        axis_val_str = str(axis_new_val)
        if axis_new_val is not None:
            path.pop(self.name)
            changed_type_path[self.name] = axis_val_str
        return (path, None, considered_axes, unmap_path, changed_type_path)

    def _find_transformed_axis_indices(self, datacube, axis, subarray, already_has_indexes):
        # NOTE: needs to be in new type
        # transformation = self.generate_final_transformation()
        if not already_has_indexes:
            indexes = datacube.datacube_natural_indexes(axis, subarray)
            # indexes = [transformation.transform_type(i) for i in indexes]
            return indexes
        else:
            pass


class TypeChangeStrToInt(DatacubeAxisTypeChange):
    def __init__(self, axis_name, new_type):
        self.axis_name = axis_name
        self._new_type = new_type

    def transform_type(self, value):
        return int(value)

    def make_str(self, value):
        return str(value)


_type_to_datacube_type_change_lookup = {"int": "TypeChangeStrToInt"}
