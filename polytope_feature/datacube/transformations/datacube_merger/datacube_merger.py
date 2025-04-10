import logging

import numpy as np
import pandas as pd

from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options, datacube=None):
        self.transformation_options = merge_options
        self.name = name
        self._first_axis = name
        self._second_axis = merge_options.other_axis
        self._linkers = merge_options.linkers
        self._merged_values = self.merged_values(datacube)

    def blocked_axes(self):
        return [self._second_axis]

    def unwanted_axes(self):
        return []

    def _mapped_axes(self):
        return self._first_axis

    def merged_values(self, datacube):
        first_ax_vals = np.array(datacube.ax_vals(self.name))
        second_ax_name = self._second_axis
        second_ax_vals = np.array(datacube.ax_vals(second_ax_name))
        linkers = self._linkers
        first_grid, second_grid = np.meshgrid(first_ax_vals, second_ax_vals, indexing="ij")
        combined_strings = np.char.add(
            np.char.add(first_grid.ravel(), linkers[0]), np.char.add(second_grid.ravel(), linkers[1])
        )
        # merged_values = pd.to_datetime(combined_strings).to_numpy().astype("datetime64[s]")
        # merged_values = np.array(merged_values)
        merged_values = pd.to_datetime(combined_strings).values.astype("datetime64[s]")
        merged_values.sort()
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
        merged_strs = np.asarray(merged_val).astype(str)

        linker1 = self._linkers[0]
        linker2 = self._linkers[1]
        len_l2 = len(linker2)

        merged_series = pd.Series(merged_strs)
        split_1 = merged_series.str.split(linker1, n=1, expand=True)
        first_vals = split_1[0]
        remainder = split_1[1]
        if len_l2 > 0:
            second_vals = remainder.str[:-len_l2]
        else:
            second_vals = remainder

        first_vals = first_vals.str.replace("-", "", regex=False)
        second_vals = second_vals.str.replace(":", "", regex=False)

        return tuple(first_vals), tuple(second_vals)

    def change_val_type(self, axis_name, values):
        new_values = pd.to_datetime(values)
        return new_values

    def find_modified_indexes(self, indexes, path, datacube, axis):
        if axis.name == self._first_axis:
            return self._merged_values

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
