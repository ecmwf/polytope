import bisect

from ..datacube_mappers import DatacubeMapper


class LocalRegularGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, md5_hash=None, local_area=[], axis_reversed=None):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
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

    def first_axis_vals(self):
        if self._axis_reversed[self._mapped_axes[0]]:
            first_ax_vals = [
                self._first_axis_max - i * self._first_deg_increment for i in range(self.first_resolution + 1)
            ]
        else:
            first_ax_vals = [
                self._first_axis_min + i * self._first_deg_increment for i in range(self.first_resolution + 1)
            ]
        return first_ax_vals

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        second_ax_vals = [
            self._second_axis_min + i * self._second_deg_increment for i in range(self.second_resolution + 1)
        ]
        return second_ax_vals

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_regular_idx(self, first_idx, second_idx):
        final_idx = first_idx * (self.second_resolution + 1) + second_idx
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
        return first_idx * self.second_resolution

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
