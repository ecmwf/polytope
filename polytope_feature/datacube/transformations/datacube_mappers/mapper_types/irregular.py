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
            )
        )
        return transformation

    def grid_latlon_points(self):
        return self._final_irregular_transformation.grid_latlon_points()

    def unmap(self, first_val, second_val, unmapped_idx=None):
        # To unmap for the irregular grid, need the request tree
        # Suppose we get the idx value somehow from the tree, as an idx input
        return unmapped_idx[0]

    def _cached_points(self):
        """Cache the (lat, lon) point cloud: `grid_latlon_points()` can be expensive
        (eg. involves reading an external grid definition for ICON), and the canonical
        index of an unstructured/irregular grid point is just its position in this list.
        """
        if getattr(self, "_points_cache", None) is None:
            self._points_cache = self.grid_latlon_points()
        return self._points_cache

    def point_count(self):
        return len(self._cached_points())

    def latlon_for_indices(self, indices):
        import numpy as np

        points = self._cached_points()
        lats = np.asarray([p[0] for p in points], dtype=np.float64)
        lons = np.asarray([p[1] for p in points], dtype=np.float64)
        return lats[np.asarray(indices, dtype=np.int64)], lons[np.asarray(indices, dtype=np.int64)]


_type_to_datacube_irregular_mapper_lookup = {
    "lambert_conformal": "LambertConformalGridMapper",
    "unstructured": "UnstructuredGridMapper",
    "icon": "ICONGridMapper",
}
