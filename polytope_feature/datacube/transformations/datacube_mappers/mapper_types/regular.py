import bisect

from ..datacube_mappers import DatacubeMapper


class RegularGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, md5_hash=None, local_area=[], axis_reversed=None):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self.deg_increment = 90 / self._resolution
        if axis_reversed is None:
            self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        else:
            assert set(axis_reversed.keys()) == set(mapped_axes)
            self._axis_reversed = axis_reversed
        self._first_axis_vals = self.first_axis_vals()
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)
        if self._axis_reversed[mapped_axes[1]]:
            raise NotImplementedError("Regular grid with second axis in decreasing order is not supported")

    def first_axis_vals(self):
        if self._axis_reversed[self._mapped_axes[0]]:
            first_ax_vals = [90 - i * self.deg_increment for i in range(2 * self._resolution)]
        else:
            first_ax_vals = [-90 + i * self.deg_increment for i in range(2 * self._resolution)]
        return first_ax_vals

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        second_ax_vals = [i * self.deg_increment for i in range(4 * self._resolution)]
        return second_ax_vals

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_regular_idx(self, first_idx, second_idx):
        final_idx = first_idx * 4 * self._resolution + second_idx
        return final_idx

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_axis_vals = self.second_axis_vals(first_val)
        second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        return second_idx

    def unmap_first_val_to_start_line_idx(self, first_val):
        tol = 1e-8
        first_val = [i for i in self._first_axis_vals if first_val - tol <= i <= first_val + tol][0]
        first_idx = self._first_axis_vals.index(first_val)
        return first_idx * 4 * self._resolution

    def unmap(self, first_val, second_val):
        tol = 1e-8
        first_val = [i for i in self._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
        first_idx = self._first_axis_vals.index(first_val)
        second_val = [i for i in self.second_axis_vals(first_val) if second_val[0] - tol <= i <= second_val[0] + tol][0]
        second_idx = self.second_axis_vals(first_val).index(second_val)
        final_index = self.axes_idx_to_regular_idx(first_idx, second_idx)
        return final_index


# md5 grid hash in form {resolution : hash}
_md5_hash = {}
