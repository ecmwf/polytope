from copy import deepcopy
from importlib import import_module

from ..datacube_mappers import DatacubeMapper


class IrregularGridMapper(DatacubeMapper):
    def __init__(
        self,
        base_axis,
        mapped_axes,
        resolution,
        md5_hash=None,
        local_area=[],
        axis_reversed=None,
        mapper_options=None,
        # grid_online_path=None,
        # grid_local_directory=None,
    ):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = False
        self.compressed_grid_axes = [self._mapped_axes[1]]
        self.mapper_options = mapper_options
        self.grid_type = mapper_options.type
        self.local_area = local_area
        self.is_irregular = True
        self.md5_hash = md5_hash
        # self.grid_online_path = grid_online_path
        # self.grid_local_directory = grid_local_directory
        self._final_irregular_transformation = self.generate_final_irregular_transformation()

    def generate_final_irregular_transformation(self):
        map_type = _type_to_datacube_irregular_mapper_lookup[self.grid_type]
        module = import_module(
            "polytope_feature.datacube.transformations.datacube_mappers.mapper_types.irregular_mapper_types."
            + self.grid_type
        )
        constructor = getattr(module, map_type)
        transformation = deepcopy(
            constructor(
                self._base_axis,
                self._mapped_axes,
                self._resolution,
                self.md5_hash,
                self.local_area,
                self._axis_reversed,
                self.mapper_options,
                # self.grid_online_path,
                # self.grid_local_directory,
            )
        )
        return transformation

    def grid_latlon_points(self):
        return self._final_irregular_transformation.grid_latlon_points()

    def unmap(self, first_val, second_val, unmapped_idx=None):
        # To unmap for the irregular grid, need the request tree
        # Suppose we get the idx value somehow from the tree, as an idx input
        return unmapped_idx[0]


_type_to_datacube_irregular_mapper_lookup = {
    "lambert_conformal": "LambertConformalGridMapper",
    "unstructured": "UnstructuredGridMapper",
    "icon": "ICONGridMapper",
}
