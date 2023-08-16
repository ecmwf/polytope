from copy import deepcopy

from ..backends.datacube import configure_datacube_axis
from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisReverse(DatacubeAxisTransformation):
    def __init__(self, name, mapper_options):
        self.name = name
        self.transformation_options = mapper_options

    def generate_final_transformation(self):
        return self

    def apply_transformation(self, name, datacube, values):
        # Remove the merge option from the axis options since we have already handled it
        # so do not want to handle it again
        axis_options = deepcopy(datacube.axis_options[name]["transformation"])
        axis_options.pop("reverse")
        # Update the nested dictionary with the modified axis option for our axis
        new_datacube_axis_options = deepcopy(datacube.axis_options)
        if axis_options == {}:
            new_datacube_axis_options[name] = {}
        else:
            new_datacube_axis_options[name]["transformation"] = axis_options
        # Reconfigure the axis with the rest of its configurations
        configure_datacube_axis(new_datacube_axis_options[name], name, values, datacube)

    def transformation_axes_final(self):
        return [self.name]

    def _find_transformed_indices_between(self, axis, datacube, indexes, low, up, first_val, offset):
        sorted_indexes = indexes.sort_values()
        indexes_between = datacube._find_indexes_between(axis, sorted_indexes, low, up)
        return (offset, indexes_between)

    def _adjust_path(self, path, considered_axes=[], unmap_path={}, changed_type_path={}):
        return (path, None, considered_axes, unmap_path, changed_type_path)

    def _find_transformed_axis_indices(self, datacube, axis, subarray, already_has_indexes):
        if not already_has_indexes:
            indexes = datacube.datacube_natural_indexes(axis, subarray)
            return indexes
        else:
            pass
