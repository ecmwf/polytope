import logging

import numpy as np
import pandas as pd

from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options):
        self.transformation_options = merge_options
        self.name = name
        self._first_axis = name
        self._second_axis = merge_options.other_axis
        self._linkers = merge_options.linkers

    def blocked_axes(self):
        return [self._second_axis]

    def unwanted_axes(self):
        return []

    def _mapped_axes(self):
        return self._first_axis

    def merged_values(self, datacube):
        first_ax_vals = datacube.ax_vals(self.name)
        second_ax_name = self._second_axis
        second_ax_vals = datacube.ax_vals(second_ax_name)
        linkers = self._linkers
        merged_values = []
        for i in range(len(first_ax_vals)):
            first_val = first_ax_vals[i]
            for j in range(len(second_ax_vals)):
                second_val = second_ax_vals[j]
                val_to_add = pd.to_datetime("".join([first_val, linkers[0], second_val, linkers[1]]))
                val_to_add = val_to_add.to_numpy()
                val_to_add = val_to_add.astype("datetime64[s]")
                merged_values.append(val_to_add)
        merged_values = np.array(merged_values)
        logging.info(
            f"Merged values {first_ax_vals} on axis {self.name} and \
                     values {second_ax_vals} on axis {second_ax_name} to values {merged_values}"
        )
        return merged_values

    def transformation_axes_final(self):
        return [self._first_axis]

    def generate_final_transformation(self):
        return self

    def unmerge(self, merged_val):
        first_values = []
        second_values = []
        for merged_value in merged_val:
            merged_val = str(merged_value)
            first_idx = merged_val.find(self._linkers[0])
            first_val = merged_val[:first_idx]
            first_linker_size = len(self._linkers[0])
            second_linked_size = len(self._linkers[1])
            second_val = merged_val[first_idx + first_linker_size : -second_linked_size]

            # TODO: maybe replacing like this is too specific to time/dates?
            first_val = str(first_val).replace("-", "")
            second_val = second_val.replace(":", "")
            logging.info(
                f"Unmerged value {merged_val} to values {first_val} on axis {self.name} \
                        and {second_val} on axis {self._second_axis}"
            )
            first_values.append(first_val)
            second_values.append(second_val)
        return (tuple(first_values), tuple(second_values))

    def change_val_type(self, axis_name, values):
        new_values = pd.to_datetime(values)
        return new_values

    def find_modified_indexes(self, indexes, path, datacube, axis):
        if axis.name == self._first_axis:
            return self.merged_values(datacube)

    def unmap_path_key(self, key_value_path, leaf_path, unwanted_path, axis):
        new_key_value_path = {}
        value = key_value_path[axis.name]
        if axis.name == self._first_axis:
            (first_val, second_val) = self.unmerge(value)
            new_key_value_path[self._first_axis] = first_val
            new_key_value_path[self._second_axis] = second_val
        return (new_key_value_path, leaf_path, unwanted_path)

    def unmap_tree_node(self, node, unwanted_path):
        if node.axis.name == self._first_axis:
            (new_first_vals, new_second_vals) = self.unmerge(node.values)
            node.values = new_first_vals
            interm_node = node.add_node_layer_after(self._second_axis, new_second_vals)
        return (interm_node, unwanted_path)
