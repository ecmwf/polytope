from polytope_feature.polytope_rs import (
    first_axis_vals_octahedral,
    unmap_octahedral,
)

from .....utility.list_tools import bisect_left_cmp, bisect_right_cmp
from ..datacube_mappers import DatacubeMapper


class OctahedralGridMapper(DatacubeMapper):
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
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self.is_irregular = False
        self._first_axis_vals = self.first_axis_vals()
        self._first_idx_map = self.create_first_idx_map()
        self._second_axis_spacing = {}
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        if self._axis_reversed[mapped_axes[1]]:
            raise NotImplementedError("Octahedral grid with second axis in decreasing order is not supported")
        if not self._axis_reversed[mapped_axes[0]]:
            raise NotImplementedError("Octahedral grid with first axis in increasing order is not supported")
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)

        if local_area != []:
            raise NotImplementedError("Local area grid not implemented for octahedral grids")

    def first_axis_vals(self):
        return first_axis_vals_octahedral(self._resolution)

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        end_idx = bisect_left_cmp(axis_lines, lower, cmp=lambda x, y: x > y) + 1
        start_idx = bisect_right_cmp(axis_lines, upper, cmp=lambda x, y: x > y)
        return_vals = axis_lines[start_idx:end_idx]
        return return_vals

    def second_axis_vals(self, first_val):
        first_axis_vals = self._first_axis_vals
        tol = 1e-10
        first_idx = bisect_left_cmp(first_axis_vals, first_val[0] - tol, cmp=lambda x, y: x > y)
        if first_idx >= self._resolution:
            first_idx = (2 * self._resolution) - 1 - first_idx
        first_idx = first_idx + 1
        npoints = 4 * first_idx + 16
        second_axis_spacing = 360 / npoints
        second_axis_vals = [i * second_axis_spacing for i in range(npoints)]
        return second_axis_vals

    def second_axis_spacing(self, first_val):
        first_axis_vals = self._first_axis_vals
        tol = 1e-10
        _first_idx = bisect_left_cmp(first_axis_vals, first_val[0] - tol, cmp=lambda x, y: x > y)
        first_idx = _first_idx
        if first_idx >= self._resolution:
            first_idx = (2 * self._resolution) - 1 - first_idx
        first_idx = first_idx + 1
        npoints = 4 * first_idx + 16
        second_axis_spacing = 360 / npoints
        return (second_axis_spacing, _first_idx + 1)

    def map_second_axis(self, first_val, lower, upper):
        second_axis_spacing, first_idx = self.second_axis_spacing(first_val)
        start_idx = int(lower / second_axis_spacing)
        end_idx = int(upper / second_axis_spacing) + 1
        return_vals = [i * second_axis_spacing for i in range(start_idx, end_idx)]
        return return_vals

    def axes_idx_to_octahedral_idx(self, first_idx, second_idx):
        # NOTE: for now this takes ~2e-4s per point, so taking significant time -> for 20k points, takes 4s
        # Would it be better to store a dictionary of first_idx with cumulative number of points on that idx?
        # Because this is what we are doing here, but we are calculating for each point...
        # But then this would only work for special grid resolutions, so need to do like a O1280 version of this

        # NOTE: OR somehow cache this for a given first_idx and then only modify the axis idx for second_idx when the
        # first_idx changes
        octa_idx = self._first_idx_map[first_idx - 1] + second_idx
        return octa_idx

    def create_first_idx_map(self):
        first_idx_list = {}
        idx = 0
        for i in range(2 * self._resolution):
            first_idx_list[i] = idx
            if i <= self._resolution - 1:
                idx += 20 + 4 * i
            else:
                i = i - self._resolution + 1
                if i == 1:
                    idx += 16 + 4 * self._resolution
                else:
                    i = i - 1
                    idx += 16 + 4 * (self._resolution - i)
        return first_idx_list

    def unmap(self, first_val, second_vals, unmapped_idx=None):
        return unmap_octahedral(self._resolution, first_val, second_vals)


# md5 grid hash in form {resolution : hash}
_md5_hash = {
    1280: "158db321ae8e773681eeb40e0a3d350f",
    2560: "b46ef646819838ead0a38749197e17a9",
}
