import bisect

from .datacube_reverse import DatacubeAxisReverse


def reverse(cls):
    if cls.reorder:

        def find_indexes(path, datacube):
            # first, find the relevant transformation object that is a mapping in the cls.transformation dico
            subarray = datacube.dataarray.sel(path, method="nearest")
            unordered_indices = datacube.datacube_natural_indexes(cls, subarray)
            if cls.name in datacube.complete_axes:
                ordered_indices = unordered_indices.sort_values()
            else:
                ordered_indices = unordered_indices
            return ordered_indices

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisReverse):
                    transformation = transform
                    if cls.name == transformation.name:
                        for indexes in index_ranges:
                            if cls.name in datacube.complete_axes:
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
                                    indexes_between_ranges.append(indexes_between)
                                else:
                                    start = indexes.searchsorted(low, "left")
                                    end = indexes.searchsorted(up, "right")
                                    indexes_between = indexes[start:end].to_list()
                                    indexes_between_ranges.append(indexes_between)
                            else:
                                if method == "surrounding" or method == "nearest":
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
        cls.find_indices_between = find_indices_between

    return cls
