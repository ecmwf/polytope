from copy import deepcopy

from ..backends.datacube import configure_datacube_axis
from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisCyclic(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, cyclic_options):
        self.name = name
        self.transformation_options = cyclic_options
        self.range = cyclic_options

    def generate_final_transformation(self):
        return self

    def transformation_axes_final(self):
        return [self.name]

    def apply_transformation(self, name, datacube, values):
        # NOTE: we will handle all the cyclicity mapping here instead of in the DatacubeAxis
        # then we can generate just create_standard in the configure_axis at the end
        # Also, in the datacube implementations, we then have to deal with the transformation dico
        # and see if there is a cyclic axis, where we then need to generate the relevant offsets etc
        # from the transformation object

        # OR, we generate a transformation, which we call in a new function create_axis.
        # In create_axis, if we have a cyclic transformation, we generate a cyclic axis, else, a standard one

        axis_options = deepcopy(datacube.axis_options[name]["transformation"])
        axis_options.pop("cyclic")
        # Update the nested dictionary with the modified axis option for our axis
        new_datacube_axis_options = deepcopy(datacube.axis_options)
        # if we have no transformations left, then empty the transformation dico
        if axis_options == {}:
            new_datacube_axis_options[name] = {}
        else:
            new_datacube_axis_options[name]["transformation"] = axis_options
        configure_datacube_axis(new_datacube_axis_options[name], name, values, datacube)

    def _find_transformed_indices_between(self, axis, datacube, indexes, low, up, first_val, offset):
        indexes_between = datacube._find_indexes_between(axis, indexes, low, up)
        return (offset, indexes_between)

    def _adjust_path(self, path, considered_axes=[], unmap_path={}, changed_type_path={}):
        return (path, None, considered_axes, unmap_path, changed_type_path)

    def _find_transformed_axis_indices(self, datacube, axis, subarray, already_has_indexes):
        if not already_has_indexes:
            indexes = datacube.datacube_natural_indexes(axis, subarray)
            return indexes
        else:
            pass
