from .datacube_mappers import DatacubeMapper


def mapper(cls):
    if cls.has_mapper:

        def find_indexes(path, datacube):
            # first, find the relevant transformation object that is a mapping in the cls.transformation dico
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name == transformation._mapped_axes()[0]:
                        return transformation.first_axis_vals()
                    if cls.name == transformation._mapped_axes()[1]:
                        first_val = path[transformation._mapped_axes()[0]]
                        return transformation.second_axis_vals(first_val)

        old_unmap_path_key = cls.unmap_path_key

        def unmap_path_key(key_value_path, leaf_path, unwanted_path):
            key_value_path, leaf_path, unwanted_path = old_unmap_path_key(key_value_path, leaf_path, unwanted_path)
            value = key_value_path[cls.name]
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    if cls.name == transform._mapped_axes()[0]:
                        unwanted_val = key_value_path[transform._mapped_axes()[0]]
                        unwanted_path[cls.name] = unwanted_val
                    if cls.name == transform._mapped_axes()[1]:
                        first_val = unwanted_path[transform._mapped_axes()[0]]
                        unmapped_idx = transform.unmap(first_val, value)
                        leaf_path.pop(transform._mapped_axes()[0], None)
                        key_value_path.pop(cls.name)
                        key_value_path[transform.old_axis] = unmapped_idx
            return (key_value_path, leaf_path, unwanted_path)

        # cls.find_indexes = find_indexes
        cls.unmap_path_key = unmap_path_key

    return cls
