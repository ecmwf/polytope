import bisect
import math

from ..datacube_mappers import DatacubeMapper


class HealpixGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, local_area=[]):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        self._first_axis_vals = self.first_axis_vals()

    def first_axis_vals(self):
        rad2deg = 180 / math.pi
        vals = [0] * (4 * self._resolution - 1)

        # Polar caps
        for i in range(1, self._resolution):
            val = 90 - (rad2deg * math.acos(1 - (i * i / (3 * self._resolution * self._resolution))))
            vals[i - 1] = val
            vals[4 * self._resolution - 1 - i] = -val
        # Equatorial belts
        for i in range(self._resolution, 2 * self._resolution):
            val = 90 - (rad2deg * math.acos((4 * self._resolution - 2 * i) / (3 * self._resolution)))
            vals[i - 1] = val
            vals[4 * self._resolution - 1 - i] = -val
        # Equator
        vals[2 * self._resolution - 1] = 0
        return vals

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        tol = 1e-8
        first_val = [i for i in self._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
        idx = self._first_axis_vals.index(first_val)

        # Polar caps
        if idx < self._resolution - 1 or 3 * self._resolution - 1 < idx <= 4 * self._resolution - 2:
            start = 45 / (idx + 1)
            vals = [start + i * (360 / (4 * (idx + 1))) for i in range(4 * (idx + 1))]
            return vals
        # Equatorial belts
        start = 45 / self._resolution
        if self._resolution - 1 <= idx < 2 * self._resolution - 1 or 2 * self._resolution <= idx < 3 * self._resolution:
            r_start = start * (2 - (((idx + 1) - self._resolution + 1) % 2))
            vals = [r_start + i * (360 / (4 * self._resolution)) for i in range(4 * self._resolution)]
            if vals[-1] == 360:
                vals[-1] = 0
            return vals
        # Equator
        temp_val = 1 if self._resolution % 2 else 0
        r_start = start * (1 - temp_val)
        if idx == 2 * self._resolution - 1:
            vals = [r_start + i * (360 / (4 * self._resolution)) for i in range(4 * self._resolution)]
            return vals

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_healpix_idx(self, first_idx, second_idx):
        idx = 0
        for i in range(self._resolution - 1):
            if i != first_idx:
                idx += 4 * (i + 1)
            else:
                idx += second_idx
                return idx
        for i in range(self._resolution - 1, 3 * self._resolution):
            if i != first_idx:
                idx += 4 * self._resolution
            else:
                idx += second_idx
                return idx
        for i in range(3 * self._resolution, 4 * self._resolution - 1):
            if i != first_idx:
                idx += 4 * (4 * self._resolution - 1 - i + 1)
            else:
                idx += second_idx
                return idx

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_axis_vals = self.second_axis_vals(first_val)
        second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        return second_idx

    def unmap_first_val_to_start_line_idx(self, first_val):
        tol = 1e-8
        first_val = [i for i in self._first_axis_vals if first_val - tol <= i <= first_val + tol][0]
        first_idx = self._first_axis_vals.index(first_val)
        idx = 0
        for i in range(self._resolution - 1):
            if i != first_idx:
                idx += 4 * (i + 1)
            else:
                return idx
        for i in range(self._resolution - 1, 3 * self._resolution):
            if i != first_idx:
                idx += 4 * self._resolution
            else:
                return idx
        for i in range(3 * self._resolution, 4 * self._resolution - 1):
            if i != first_idx:
                idx += 4 * (4 * self._resolution - 1 - i + 1)
            else:
                return idx

    def unmap(self, first_val, second_val):
        tol = 1e-8
        first_value = [i for i in self._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
        first_idx = self._first_axis_vals.index(first_value)
        second_val = [i for i in self.second_axis_vals(first_val) if second_val[0] - tol <= i <= second_val[0] + tol][0]
        second_idx = self.second_axis_vals(first_val).index(second_val)
        healpix_index = self.axes_idx_to_healpix_idx(first_idx, second_idx)
        return healpix_index
