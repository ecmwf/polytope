import math
from copy import deepcopy

from ....utility.combinatorics import unique
from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisCyclic(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, cyclic_options):
        self.name = name
        self.transformation_options = cyclic_options
        self.range = cyclic_options.range

    def generate_final_transformation(self):
        return self

    def transformation_axes_final(self):
        return [self.name]

    def change_val_type(self, axis_name, values):
        return values

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return []

    def update_range(self, axis):
        axis.range = self.range

    def _remap_range_to_axis_range(self, range, axis):
        self.update_range(axis)
        axis_lower = axis.range[0]
        axis_upper = axis.range[1]
        axis_range = axis_upper - axis_lower
        lower = range[0]
        upper = range[1]
        if lower < axis_lower:
            # In this case we need to calculate the number of loops between the axis lower
            # and the lower to recenter the lower
            loops = int((axis_lower - lower - axis.tol) / axis_range)
            return_lower = lower + (loops + 1) * axis_range
            return_upper = upper + (loops + 1) * axis_range
        elif lower >= axis_upper:
            # In this case we need to calculate the number of loops between the axis upper
            # and the lower to recenter the lower
            loops = int((lower - axis_upper) / axis_range)
            return_lower = lower - (loops + 1) * axis_range
            return_upper = upper - (loops + 1) * axis_range
        else:
            # In this case, the lower value is already in the right range
            return_lower = lower
            return_upper = upper
        return [return_lower, return_upper]

    def _remap_val_to_axis_range(self, value, axis):
        value = self._remap_range_to_axis_range([value, value], axis)
        return value[0]

    def offset(self, range, axis, offset):
        # We first unpad the range by the axis tolerance to make sure that
        # we find the wanted range of the cyclic axis since we padded by the axis tolerance before.
        # Also, it's safer that we find the offset of a value inside the range instead of on the border
        unpadded_range = [range[0] + 1.5 * axis.tol, range[1] - 1.5 * axis.tol]
        cyclic_range = self._remap_range_to_axis_range(unpadded_range, axis)
        offset = unpadded_range[0] - cyclic_range[0]
        return offset

    def remap(self, range, ranges, axis):
        self.update_range(axis)
        if axis.range[0] - axis.tol <= range[0] <= axis.range[1] + axis.tol:
            if axis.range[0] - axis.tol <= range[1] <= axis.range[1] + axis.tol:
                # If we are already in the cyclic range, return it
                return [range]
        elif abs(range[0] - range[1]) <= 2 * axis.tol:
            # If we have a range that is just one point, then it should still be counted
            # and so we should take a small interval around it to find values inbetween
            range = [
                self._remap_val_to_axis_range(range[0], axis) - axis.tol,
                self._remap_val_to_axis_range(range[0], axis) + axis.tol,
            ]
            return [range]
        range_intervals = self.to_intervals(range, [[]], axis)
        ranges = []
        for interval in range_intervals:
            if abs(interval[0] - interval[1]) > 0:
                # If the interval is not just a single point, we remap it to the axis range
                range = self._remap_range_to_axis_range([interval[0], interval[1]], axis)
                up = range[1]
                low = range[0]
                if up < low:
                    # Make sure we remap in the right order
                    ranges.append([up - axis.tol, low + axis.tol])
                else:
                    ranges.append([low - axis.tol, up + axis.tol])
        return ranges

    def to_intervals(self, range, intervals, axis):
        self.update_range(axis)
        if range[0] == -math.inf:
            range[0] = axis.range[0]
        if range[1] == math.inf:
            range[1] = axis.range[1]
        axis_lower = axis.range[0]
        axis_upper = axis.range[1]
        axis_range = axis_upper - axis_lower
        lower = range[0]
        upper = range[1]
        intervals = []
        if lower < axis_upper:
            # In this case, we want to go from lower to the first remapped cyclic axis upper
            # or the asked upper range value.
            # For example, if we have cyclic range [0,360] and we want to break [-270,180] into intervals,
            # we first want to obtain [-270, 0] as the first range, where 0 is the remapped cyclic axis upper
            # but if we wanted to break [-270, -180] into intervals, we would want to get [-270,-180],
            # where -180 is the asked upper range value.
            loops = int((axis_upper - lower) / axis_range)
            remapped_up = axis_upper - (loops) * axis_range
            new_upper = min(upper, remapped_up)
        else:
            # In this case, since lower >= axis_upper, we need to either go to the asked upper range
            # or we need to go to the first remapped cyclic axis upper which is higher than lower
            new_upper = min(axis_upper + axis_range, upper)
            while new_upper < lower:
                new_upper = min(new_upper + axis_range, upper)
        intervals.append([lower, new_upper])
        # Now that we have established what the first interval should be, we should just jump from cyclic range
        # to cyclic range until we hit the asked upper range value.
        new_up = deepcopy(new_upper)
        while new_up < upper:
            new_upper = new_up
            new_up = min(upper, new_upper + axis_range)
            intervals.append([new_upper, new_up])
        # Once we have added all the in-between ranges, we need to add the last interval
        intervals.append([new_up, upper])
        return intervals

    def find_indices_between(self, indexes_ranges, low, up, datacube, method, indexes_between_ranges, axis):
        search_ranges = self.remap([low, up], [], axis)
        original_search_ranges = self.to_intervals([low, up], [], axis)
        # Find the offsets for each interval in the requested range, which we will need later
        search_ranges_offset = []
        for r in original_search_ranges:
            offset = self.offset(r, axis, 0)
            search_ranges_offset.append(offset)
        idx_between = []
        for i in range(len(search_ranges)):
            r = search_ranges[i]
            offset = search_ranges_offset[i]
            low = r[0]
            up = r[1]
            indexes_between = axis.find_standard_indices_between(indexes_ranges, low, up, datacube, method)
            # Now the indexes_between are values on the cyclic range so need to remap them to their original
            # values before returning them
            # if we have a special indexes between range that needs additional offset, treat it here
            if len(indexes_between) == 0:
                idx_between = idx_between
            else:
                for k in range(len(indexes_between)):
                    if offset is None:
                        indexes_between[k] = indexes_between[k]
                    else:
                        indexes_between[k] = round(indexes_between[k] + offset, int(-math.log10(axis.tol)))
                    idx_between.append(indexes_between[k])
        if offset is not None:
            # Note that we can only do unique if not dealing with time values
            idx_between = unique(idx_between)
        return idx_between
