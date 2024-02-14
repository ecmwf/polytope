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

        cls.find_indexes = find_indexes
        cls.unmap_path_key = unmap_path_key

    return cls
