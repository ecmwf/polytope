import numpy as np
import pandas as pd
# import time

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
    
    def unwanted_axes(self):
        return []

    def merged_values(self, datacube):
        # time1 = time.time()
        first_ax_vals = datacube.ax_vals(self.name)
        second_ax_name = self._second_axis
        second_ax_vals = datacube.ax_vals(second_ax_name)
        linkers = self._linkers
        merged_values = []
        # merged_values = np.empty(len(first_ax_vals)*len(second_ax_vals))
        # for first_val in first_ax_vals:
        for i in range(len(first_ax_vals)):
            first_val = first_ax_vals[i]
            # for second_val in second_ax_vals:
            for j in range(len(second_ax_vals)):
                second_val = second_ax_vals[j]
                # TODO: check that the first and second val are strings
                val_to_add = pd.to_datetime("".join([first_val, linkers[0], second_val, linkers[1]]))
                val_to_add = val_to_add.to_numpy()
                val_to_add = val_to_add.astype("datetime64[s]")
                merged_values.append(val_to_add)
                # print(val_to_add)
                # merged_values[i*len(second_ax_vals) + j] = val_to_add
        merged_values = np.array(merged_values)
        # print("MERGED VALUES TIME")
        # print(time.time() - time1)
        return merged_values

    def transformation_axes_final(self):
        return [self._first_axis]

    def generate_final_transformation(self):
        return self

    def unmerge(self, merged_val):
        # time1 = time.time()
        merged_val = str(merged_val)
        first_idx = merged_val.find(self._linkers[0])
        first_val = merged_val[:first_idx]
        first_linker_size = len(self._linkers[0])
        second_linked_size = len(self._linkers[1])
        second_val = merged_val[first_idx + first_linker_size : -second_linked_size]

        # TODO: maybe replacing like this is too specific to time/dates?
        first_val = str(first_val).replace("-", "")
        second_val = second_val.replace(":", "")
        # print("UNMERGE TIME")
        # print(time.time() - time1)
        return (first_val, second_val)

    def change_val_type(self, axis_name, values):
        return values
