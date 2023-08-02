import numpy as np

from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options):
        # TODO: not here, but in datacube, create a big flag dictionary where for each axis,
        # we add a flag like grid_mapper if there is a mapper or datacube_merger if there is a merger
        # with the relevant info for later. Can initalise these flags here/ add them to flag dictionary here
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

    def finish_transformation(self, datacube, values):
        datacube.blocked_axes.append(self._second_axis)
        # NOTE: we change the axis values here directly
        datacube.dataarray[self._first_axis] = self.merged_values(values, datacube)
