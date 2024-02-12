import bisect

from .datacube_type_change import DatacubeAxisTypeChange


def type_change(cls):
    if cls.type_change:
        old_find_indexes = cls.find_indexes

        def find_indexes(path, datacube):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        original_vals = old_find_indexes(path, datacube)
                        return transformation.change_val_type(cls.name, original_vals)

        old_unmap_path_key = cls.unmap_path_key

        def unmap_path_key(key_value_path, leaf_path, unwanted_path):
            key_value_path, leaf_path, unwanted_path = old_unmap_path_key(key_value_path, leaf_path, unwanted_path)
            value = key_value_path[cls.name]
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    if cls.name == transform.name:
                        unchanged_val = transform.make_str(value)
                        key_value_path[cls.name] = unchanged_val
            return (key_value_path, leaf_path, unwanted_path)

        def unmap_to_datacube(path, unmapped_path):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        changed_val = path.get(cls.name, None)
                        unchanged_val = transformation.make_str(changed_val)
                        if cls.name in path:
                            path.pop(cls.name, None)
                            unmapped_path[cls.name] = unchanged_val
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
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
