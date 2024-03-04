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

        cls.find_indexes = find_indexes
        cls.unmap_path_key = unmap_path_key

    return cls
