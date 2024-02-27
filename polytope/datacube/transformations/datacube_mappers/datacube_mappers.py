from copy import deepcopy
from importlib import import_module

from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeMapper(DatacubeAxisTransformation):
    # Needs to implements DatacubeAxisTransformation methods

    def __init__(self, name, mapper_options):
        self.transformation_options = mapper_options
        self.grid_type = mapper_options.type
        self.grid_resolution = mapper_options.resolution
        self.grid_axes = mapper_options.axes
        self.local_area = []
        if mapper_options.local is not None:
            # "local" in mapper_options.keys():
            self.local_area = mapper_options.local
        self.old_axis = name
        self._final_transformation = self.generate_final_transformation()
        self._final_mapped_axes = self._final_transformation._mapped_axes
        self._axis_reversed = self._final_transformation._axis_reversed

    def generate_final_transformation(self):
        map_type = _type_to_datacube_mapper_lookup[self.grid_type]
        module = import_module("polytope.datacube.transformations.datacube_mappers.mapper_types." + self.grid_type)
        constructor = getattr(module, map_type)
        transformation = deepcopy(constructor(self.old_axis, self.grid_axes, self.grid_resolution, self.local_area))
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
    "local_regular": "LocalRegularGridMapper",
}
