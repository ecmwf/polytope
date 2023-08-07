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
