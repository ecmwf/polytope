import bisect

from ..datacube_mappers import DatacubeMapper


class LocalRegularGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, local_area=[]):
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
        else:
            self.first_resolution = resolution[0]
            self.second_resolution = resolution[1]
        self._first_deg_increment = (local_area[1] - local_area[0]) / self.first_resolution
        self._second_deg_increment = (local_area[3] - local_area[2]) / self.second_resolution
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        self._first_axis_vals = self.first_axis_vals()
        self.compressed_grid_axes = [self._mapped_axes[1]]

    def first_axis_vals(self):
        first_ax_vals = [self._first_axis_max - i * self._first_deg_increment for i in range(self.first_resolution + 1)]
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
