import bisect

import numpy as np
import pandas as pd

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
                # TODO: check that the first and second val are strings
                val_to_add = pd.to_datetime("".join([first_val, linkers[0], second_val, linkers[1]]))
                val_to_add = val_to_add.to_numpy()
                val_to_add = val_to_add.astype("datetime64[s]")
                merged_values.append(val_to_add)
        merged_values = np.array(merged_values)
        return merged_values

    def transformation_axes_final(self):
        return [self._first_axis]

    def generate_final_transformation(self):
        return self

    def unmerge(self, merged_val):
        merged_val = str(merged_val)
        first_idx = merged_val.find(self._linkers[0])
        first_val = merged_val[:first_idx]
        first_linker_size = len(self._linkers[0])
        second_linked_size = len(self._linkers[1])
        second_val = merged_val[first_idx + first_linker_size : -second_linked_size]

        # TODO: maybe replacing like this is too specific to time/dates?
        first_val = str(first_val).replace("-", "")
        second_val = second_val.replace(":", "")
        return (first_val, second_val)

    def change_val_type(self, axis_name, values):
        new_values = pd.to_datetime(values)
        return new_values


def merge(cls):
    if cls.has_merger:

        def find_indexes(path, datacube):
            # first, find the relevant transformation object that is a mapping in the cls.transformation dico
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name == transformation._first_axis:
                        return transformation.merged_values(datacube)

        old_unmap_path_key = cls.unmap_path_key

        def unmap_path_key(key_value_path, leaf_path, unwanted_path):
            key_value_path, leaf_path, unwanted_path = old_unmap_path_key(key_value_path, leaf_path, unwanted_path)
            new_key_value_path = {}
            value = key_value_path[cls.name]
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    if cls.name == transform._first_axis:
                        (first_val, second_val) = transform.unmerge(value)
                        new_key_value_path[transform._first_axis] = first_val
                        new_key_value_path[transform._second_axis] = second_val
            return (new_key_value_path, leaf_path, unwanted_path)

        old_unmap_to_datacube = cls.unmap_to_datacube

        def unmap_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name == transformation._first_axis:
                        old_val = path.get(cls.name, None)
                        (first_val, second_val) = transformation.unmerge(old_val)
                        path.pop(cls.name, None)
                        path[transformation._first_axis] = first_val
                        path[transformation._second_axis] = second_val
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name in transformation._mapped_axes():
                        for indexes in index_ranges:
                            if method == "surrounding":
                                start = indexes.index(low)
                                end = indexes.index(up)
                                start = max(start - 1, 0)
                                end = min(end + 1, len(indexes))
                                indexes_between = indexes[start:end]
                                indexes_between_ranges.append(indexes_between)
                            else:
                                lower_idx = bisect.bisect_left(indexes, low)
                                upper_idx = bisect.bisect_right(indexes, up)
                                indexes_between = indexes[lower_idx:upper_idx]
                                indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.find_indices_between = find_indices_between
        cls.unmap_path_key = unmap_path_key

    return cls
