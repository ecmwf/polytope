import numpy as np

from polytope_feature.polytope_rs import (
    first_axis_vals_local_regular,
    unmap_local_regular,
)

from ..datacube_mappers import DatacubeMapper


class LocalRegularGridMapper(DatacubeMapper):
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

        if local_area == [] or len(local_area) != 4:
            raise TypeError("Local area grid region not or wrongly specified")

        self.is_irregular = False
        self._first_axis_min = local_area[0]
        self._first_axis_max = local_area[1]
        self._second_axis_min = local_area[2]
        self._second_axis_max = local_area[3]
        if not isinstance(resolution, list):
            self.first_resolution = resolution
            self.second_resolution = resolution
            if md5_hash is not None:
                self.md5_hash = md5_hash
            else:
                self.md5_hash = _md5_hash.get(resolution, None)
        else:
            self.first_resolution = resolution[0]
            self.second_resolution = resolution[1]
            if md5_hash is not None:
                self.md5_hash = md5_hash
            else:
                self.md5_hash = _md5_hash.get(tuple(resolution), None)
        self._first_deg_increment = (local_area[1] - local_area[0]) / self.first_resolution
        self._second_deg_increment = (local_area[3] - local_area[2]) / self.second_resolution
        if axis_reversed is None:
            self._axis_reversed = {mapped_axes[0]: False, mapped_axes[1]: False}
        else:
            assert set(axis_reversed.keys()) == set(mapped_axes)
            self._axis_reversed = axis_reversed
        self._first_axis_vals = self.first_axis_vals()
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if self._axis_reversed[mapped_axes[1]]:
            raise NotImplementedError("Local regular grid with second axis in decreasing order is not supported")

        self._second_axis_vals = np.arange(
            self._second_axis_min,
            self._second_axis_min + self._second_deg_increment * (self.second_resolution + 1),
            self._second_deg_increment,
            dtype=np.float64,
        )

    def first_axis_vals(self):
        descending = self._axis_reversed[self._mapped_axes[0]]
        return first_axis_vals_local_regular(
            self._first_axis_min,
            self._first_axis_max,
            self.first_resolution,
            descending,
        )

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        return self._second_axis_vals

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self._second_axis_vals
        return_vals = axis_lines[(axis_lines >= lower) & (axis_lines <= upper)].tolist()
        return return_vals

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_idx = np.searchsorted(self._second_axis_vals, second_val - tol)
        return int(second_idx)

    def unmap_first_val_to_start_line_idx(self, first_val):
        first_array = np.asarray(self._first_axis_vals)
        descending = self._axis_reversed[self._mapped_axes[0]]
        if descending:
            first_idx = int(np.searchsorted(-first_array, -first_val))
        else:
            first_idx = int(np.searchsorted(first_array, first_val))
        return first_idx * (self.second_resolution + 1)

    def unmap(self, first_val, second_vals, unmapped_idx=None):
        descending = self._axis_reversed[self._mapped_axes[0]]
        return unmap_local_regular(
            list(self._first_axis_vals),
            list(self._second_axis_vals),
            first_val[0],
            list(second_vals),
            descending,
            self.second_resolution,
        )


# md5 grid hash in form {resolution : hash}
_md5_hash = {}
