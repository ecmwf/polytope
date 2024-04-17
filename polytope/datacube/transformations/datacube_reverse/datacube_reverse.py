from ....utility.list_tools import bisect_left_cmp, bisect_right_cmp
from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisReverse(DatacubeAxisTransformation):
    def __init__(self, name, mapper_options):
        self.name = name
        self.transformation_options = mapper_options

    def generate_final_transformation(self):
        return self

    def transformation_axes_final(self):
        return [self.name]

    def change_val_type(self, axis_name, values):
        return values

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return []

    def find_modified_indexes(self, indexes, path, datacube, axis):
        if axis.name in datacube.complete_axes:
            ordered_indices = indexes.sort_values()
        else:
            ordered_indices = indexes
        return ordered_indices

    def find_indices_between(self, indexes, low, up, datacube, method, indexes_between_ranges, axis):
        indexes_between_ranges = []
        if axis.name == self.name:
            if axis.name in datacube.complete_axes:
                # Find the range of indexes between lower and upper
                # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
                # Assumes the indexes are already sorted (could sort to be sure) and monotonically
                # increasing
                if method == "surrounding" or method == "nearest":
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    start = max(start - 1, 0)
                    end = min(end + 1, len(indexes))
                    indexes_between = indexes[start:end].to_list()
                    indexes_between_ranges.extend(indexes_between)
                else:
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    indexes_between = indexes[start:end].to_list()
                    indexes_between_ranges.extend(indexes_between)
            else:
                if method == "surrounding" or method == "nearest":
                    end_idx = bisect_left_cmp(indexes, low, cmp=lambda x, y: x > y) + 1
                    start_idx = bisect_right_cmp(indexes, up, cmp=lambda x, y: x > y)
                    start = max(start_idx - 1, 0)
                    end = min(end_idx + 1, len(indexes))
                    indexes_between = indexes[start:end]
                    indexes_between_ranges.extend(indexes_between)
                else:
                    end_idx = bisect_left_cmp(indexes, low, cmp=lambda x, y: x > y) + 1
                    start_idx = bisect_right_cmp(indexes, up, cmp=lambda x, y: x > y)
                    indexes_between = indexes[start_idx:end_idx]
                    indexes_between_ranges.extend(indexes_between)
        return indexes_between_ranges
