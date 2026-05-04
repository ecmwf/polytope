import numpy as np

from polytope_feature.polytope_rs import first_axis_vals_regular, unmap_regular

from ..datacube_mappers import DatacubeMapper


class RegularGridMapper(DatacubeMapper):
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
        self.is_irregular = False
        self.deg_increment = 90 / self._resolution
        if axis_reversed is None:
            self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        else:
            assert set(axis_reversed.keys()) == set(mapped_axes)
            self._axis_reversed = axis_reversed
        self._first_axis_vals = self.first_axis_vals()
        # Cache second axis values — identical for every latitude row
        self._second_axis_vals = np.arange(4 * self._resolution, dtype=np.float64) * self.deg_increment
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)
        if self._axis_reversed[mapped_axes[1]]:
            raise NotImplementedError("Regular grid with second axis in decreasing order is not supported")

        if local_area != []:
            raise TypeError("Use local_regular grid type for local area regular lat-lon grids")

    def first_axis_vals(self):
        descending = self._axis_reversed[self._mapped_axes[0]]
        return first_axis_vals_regular(self._resolution, descending)

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
        first_axis_arr = np.asarray(self._first_axis_vals)
        descending = self._axis_reversed[self._mapped_axes[0]]
        if descending:
            first_idx = int(np.searchsorted(-first_axis_arr, -first_val))
        else:
            first_idx = int(np.searchsorted(first_axis_arr, first_val))
        return first_idx * 4 * self._resolution

    def unmap(self, first_val, second_vals, unmapped_idx=None):
        descending = self._axis_reversed[self._mapped_axes[0]]
        return unmap_regular(
            self._resolution,
            self._first_axis_vals,
            first_val[0],
            list(second_vals),
            descending,
        )


# md5 grid hash in form {resolution : hash}
_md5_hash = {}
