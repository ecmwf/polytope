import numpy as np

from ..backends.datacube import configure_datacube_axis
from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options):
        self.transformation_options = merge_options
        self.name = name
        self._first_axis = name
        self._second_axis = merge_options["with"]
        self._linkers = merge_options["linkers"]

    def merged_values(self, values, datacube):
        first_ax_vals = values
        second_ax_name = self._second_axis
        second_ax_vals = datacube.ax_vals(second_ax_name)
        linkers = self._linkers
        merged_values = []
        for first_val in first_ax_vals:
            for second_val in second_ax_vals:
                # TODO: check that the first and second val are strings
                merged_values.append(first_val + linkers[0] + second_val + linkers[1])
        merged_values = np.array(merged_values)
        return merged_values

    def apply_transformation(self, name, datacube, values):
        merged_values = self.merged_values(values, datacube)
        # Remove the merge option from the axis options since we have already handled it
        # so do not want to handle it again
        axis_options = datacube.axis_options[name]["transformation"]
        axis_options.pop("merge")
        # Update the nested dictionary with the modified axis option for our axis
        new_datacube_axis_options = datacube.axis_options
        new_datacube_axis_options[name]["transformation"] = axis_options
        # Reconfigure the axis with the rest of its configurations
        configure_datacube_axis(new_datacube_axis_options, name, merged_values, datacube)
        self.finish_transformation(datacube, merged_values)

    def transformation_axes_final(self):
        return [self._first_axis]

    def finish_transformation(self, datacube, values):
        # Need to "delete" the second axis we do not use anymore
        datacube.blocked_axes.append(self._second_axis)
        # NOTE: we change the axis values here directly, which will not work with xarray
        datacube.dataarray[self._first_axis] = values

    def generate_final_transformation(self):
        return self
