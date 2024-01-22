import bisect
from copy import deepcopy
from importlib import import_module

from ...utility.list_tools import bisect_left_cmp, bisect_right_cmp
from .datacube_transformations import DatacubeAxisTransformation


class DatacubeMapper(DatacubeAxisTransformation):
    # Needs to implements DatacubeAxisTransformation methods

    def __init__(self, name, mapper_options):
        self.transformation_options = mapper_options
        self.grid_type = mapper_options["type"]
        self.grid_resolution = mapper_options["resolution"]
        self.grid_axes = mapper_options["axes"]
        self.old_axis = name
        self._final_transformation = self.generate_final_transformation()
        self._final_mapped_axes = self._final_transformation._mapped_axes
        self._axis_reversed = self._final_transformation._axis_reversed

    def generate_final_transformation(self):
        map_type = _type_to_datacube_mapper_lookup[self.grid_type]
        module = import_module("polytope.datacube.transformations.mappers." + self.grid_type)
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.old_axis, self.grid_axes, self.grid_resolution))
        return transformation

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return [self._final_mapped_axes[0]]

    def transformation_axes_final(self):
        final_axes = self._final_mapped_axes
        return final_axes

    # Needs to also implement its own methods

    def change_val_type(self, axis_name, values):
        # the new axis_vals created will be floats
        return [0.0]

    def _mapped_axes(self):
        # NOTE: Each of the mapper method needs to call it's sub mapper method
        final_axes = self._final_mapped_axes
        return final_axes

    def _base_axis(self):
        pass

    def _resolution(self):
        pass

    def first_axis_vals(self):
        return self._final_transformation.first_axis_vals()

    def second_axis_vals(self, first_val):
        return self._final_transformation.second_axis_vals(first_val)

    def map_first_axis(self, lower, upper):
        return self._final_transformation.map_first_axis(lower, upper)

    def map_second_axis(self, first_val, lower, upper):
        return self._final_transformation.map_second_axis(first_val, lower, upper)

    def find_second_idx(self, first_val, second_val):
        return self._final_transformation.find_second_idx(first_val, second_val)

    def unmap_first_val_to_start_line_idx(self, first_val):
        return self._final_transformation.unmap_first_val_to_start_line_idx(first_val)

    def unmap(self, first_val, second_val):
        return self._final_transformation.unmap(first_val, second_val)


_type_to_datacube_mapper_lookup = {
    "octahedral": "OctahedralGridMapper",
    "healpix": "HealpixGridMapper",
    "regular": "RegularGridMapper",
    "reduced_ll": "ReducedLatLonMapper",
}


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

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name in transformation._mapped_axes():
                        for idxs in index_ranges:
                            if method == "surrounding":
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
