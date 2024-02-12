import bisect

from .datacube_merger import DatacubeAxisMerger


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
            for indexes in index_ranges:
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
        cls.unmap_to_datacube = unmap_to_datacube
        cls.find_indices_between = find_indices_between
        cls.unmap_path_key = unmap_path_key

    return cls
