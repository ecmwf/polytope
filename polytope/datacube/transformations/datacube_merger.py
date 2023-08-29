from copy import deepcopy

import numpy as np
import pandas as pd

# from ..backends.datacube import configure_datacube_axis
from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options):
        self.transformation_options = merge_options
        self.name = name
        self._first_axis = name
        self._second_axis = merge_options["with"]
        self._linkers = merge_options["linkers"]

    def blocked_axes(self):
        return [self._second_axis]

    def merged_values(self, datacube):
        first_ax_vals = datacube.ax_vals(self.name)
        second_ax_name = self._second_axis
        second_ax_vals = datacube.ax_vals(second_ax_name)
        linkers = self._linkers
        merged_values = []
        for first_val in first_ax_vals:
            for second_val in second_ax_vals:
                # TODO: check that the first and second val are strings
                # merged_values.append(np.datetime64(first_val + linkers[0] + second_val + linkers[1]))
                val_to_add = pd.to_datetime(first_val + linkers[0] + second_val + linkers[1])
                val_to_add = val_to_add.to_numpy()
                val_to_add = val_to_add.astype("datetime64[s]")
                # merged_values.append(pd.to_datetime(first_val + linkers[0] + second_val + linkers[1]))
                # val_to_add = str(val_to_add)
                merged_values.append(val_to_add)
        merged_values = np.array(merged_values)
        return merged_values

    # def apply_transformation(self, name, datacube, values):
    #     merged_values = self.merged_values(datacube)
    #     # Remove the merge option from the axis options since we have already handled it
    #     # so do not want to handle it again
    #     axis_options = deepcopy(datacube.axis_options[name]["transformation"])
    #     axis_options.pop("merge")
    #     # Update the nested dictionary with the modified axis option for our axis
    #     new_datacube_axis_options = deepcopy(datacube.axis_options)
    #     if axis_options == {}:
    #         new_datacube_axis_options[name] = {}
    #     else:
    #         new_datacube_axis_options[name]["transformation"] = axis_options
    #     # Reconfigure the axis with the rest of its configurations
    #     configure_datacube_axis(new_datacube_axis_options[name], name, merged_values, datacube)
    #     self.finish_transformation(datacube, merged_values)

    def transformation_axes_final(self):
        return [self._first_axis]

    def finish_transformation(self, datacube, values):
        # Need to "delete" the second axis we do not use anymore
        datacube.blocked_axes.append(self._second_axis)

    def generate_final_transformation(self):
        return self

    def unmerge(self, merged_val):
        merged_val = str(merged_val)
        first_idx = merged_val.find(self._linkers[0])
        # second_idx = merged_val.find(self._linkers[1])
        first_val = merged_val[:first_idx]
        first_linker_size = len(self._linkers[0])
        second_linked_size = len(self._linkers[1])
        second_val = merged_val[first_idx + first_linker_size : -second_linked_size]
        return (first_val, second_val)

    def change_val_type(self, axis_name, values):
        return values

    def _find_transformed_indices_between(self, axis, datacube, indexes, low, up, first_val, offset):
        indexes_between = datacube._find_indexes_between(axis, indexes, low, up)
        return (offset, indexes_between)

    def _adjust_path(self, path, considered_axes=[], unmap_path={}, changed_type_path={}):
        merged_ax = self._first_axis
        merged_val = path.get(merged_ax, None)
        removed_ax = self._second_axis
        path.pop(removed_ax, None)
        path.pop(merged_ax, None)
        if merged_val is not None:
            unmapped_first_val = self.unmerge(merged_val)[0]
            unmapped_second_val = self.unmerge(merged_val)[1]
            unmap_path[merged_ax] = unmapped_first_val
            unmap_path[removed_ax] = unmapped_second_val
        return (path, None, considered_axes, unmap_path, changed_type_path)

    def _find_transformed_axis_indices(self, datacube, axis, subarray, already_has_indexes):
        datacube.complete_axes.remove(axis.name)
        indexes = self.merged_values(datacube)
        return indexes