import bisect

from ....utility.list_tools import bisect_left_cmp, bisect_right_cmp
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
                            unmapped_idx = path.get("result", None)
                            unmapped_idx = transform.unmap(first_val, second_val, unmapped_idx)
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
                        unmapped_idx = leaf_path.get("result", None)
                        unmapped_idx = transform.unmap(first_val, value, unmapped_idx)
                        leaf_path.pop(transform._mapped_axes()[0], None)
                        key_value_path.pop(cls.name)
                        key_value_path[transform.old_axis] = unmapped_idx
            return (key_value_path, leaf_path, unwanted_path)

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name in transformation._mapped_axes():
                        for idxs in index_ranges:
                            if method == "surrounding" or method == "nearest":
                                axis_reversed = transform._axis_reversed[cls.name]
                                if not axis_reversed:
                                    start = bisect.bisect_left(idxs, low)
                                    end = bisect.bisect_right(idxs, up)
                                else:
                                    # TODO: do the custom bisect
                                    end = bisect_left_cmp(idxs, low, cmp=lambda x, y: x > y) + 1
                                    start = bisect_right_cmp(idxs, up, cmp=lambda x, y: x > y)
                                start = max(start - 1, 0)
                                end = min(end + 1, len(idxs))
                                indexes_between = idxs[start:end]
                                indexes_between_ranges.append(indexes_between)
                            else:
                                axis_reversed = transform._axis_reversed[cls.name]
                                if not axis_reversed:
                                    lower_idx = bisect.bisect_left(idxs, low)
                                    upper_idx = bisect.bisect_right(idxs, up)
                                    indexes_between = idxs[lower_idx:upper_idx]
                                else:
                                    # TODO: do the custom bisect
                                    end_idx = bisect_left_cmp(idxs, low, cmp=lambda x, y: x > y) + 1
                                    start_idx = bisect_right_cmp(idxs, up, cmp=lambda x, y: x > y)
                                    indexes_between = idxs[start_idx:end_idx]
                                indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.find_indices_between = find_indices_between
        cls.unmap_path_key = unmap_path_key

    return cls
