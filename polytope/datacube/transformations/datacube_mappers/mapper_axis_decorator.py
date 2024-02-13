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

        old_unmap_to_datacube = cls.unmap_to_datacube

        def unmap_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    if cls.name == transform._mapped_axes()[0]:
                        # if we are on the first axis, then need to add the first val to unmapped_path
                        first_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        if cls.name not in unmapped_path:
                            # if for some reason, the unmapped_path already has the first axis val, then don't update
                            unmapped_path[cls.name] = first_val
                    if cls.name == transform._mapped_axes()[1]:
                        # if we are on the second axis, then the val of the first axis is stored
                        # inside unmapped_path so can get it from there
                        second_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        first_val = unmapped_path.get(transform._mapped_axes()[0], None)
                        unmapped_path.pop(transform._mapped_axes()[0], None)
                        # if the first_val was not in the unmapped_path, then it's still in path
                        if first_val is None:
                            first_val = path.get(transform._mapped_axes()[0], None)
                            path.pop(transform._mapped_axes()[0], None)
                        if first_val is not None and second_val is not None:
                            unmapped_idx = transform.unmap(first_val, second_val)
                            unmapped_path[transform.old_axis] = unmapped_idx
            return (path, unmapped_path)

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

        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.unmap_path_key = unmap_path_key

    return cls
