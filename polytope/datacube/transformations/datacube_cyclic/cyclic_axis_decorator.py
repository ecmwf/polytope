import math
from copy import deepcopy
from typing import List

from ....utility.combinatorics import unique
from .datacube_cyclic import DatacubeAxisCyclic


def cyclic(cls):
    if cls.is_cyclic:

        def update_range():
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisCyclic):
                    transformation = transform
                    cls.range = transformation.range

        def to_intervals(range):
            update_range()
            if range[0] == -math.inf:
                range[0] = cls.range[0]
            if range[1] == math.inf:
                range[1] = cls.range[1]
            axis_lower = cls.range[0]
            axis_upper = cls.range[1]
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

        def _remap_range_to_axis_range(range):
            update_range()
            axis_lower = cls.range[0]
            axis_upper = cls.range[1]
            axis_range = axis_upper - axis_lower
            lower = range[0]
            upper = range[1]
            if lower < axis_lower:
                # In this case we need to calculate the number of loops between the axis lower
                # and the lower to recenter the lower
                loops = int((axis_lower - lower - cls.tol) / axis_range)
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

        def _remap_val_to_axis_range(value):
            return_range = _remap_range_to_axis_range([value, value])
            return return_range[0]

        def remap(range: List):
            update_range()
            if cls.range[0] - cls.tol <= range[0] <= cls.range[1] + cls.tol:
                if cls.range[0] - cls.tol <= range[1] <= cls.range[1] + cls.tol:
                    # If we are already in the cyclic range, return it
                    return [range]
            elif abs(range[0] - range[1]) <= 2 * cls.tol:
                # If we have a range that is just one point, then it should still be counted
                # and so we should take a small interval around it to find values inbetween
                range = [
                    _remap_val_to_axis_range(range[0]) - cls.tol,
                    _remap_val_to_axis_range(range[0]) + cls.tol,
                ]
                return [range]
            range_intervals = cls.to_intervals(range)
            ranges = []
            for interval in range_intervals:
                if abs(interval[0] - interval[1]) > 0:
                    # If the interval is not just a single point, we remap it to the axis range
                    range = _remap_range_to_axis_range([interval[0], interval[1]])
                    up = range[1]
                    low = range[0]
                    if up < low:
                        # Make sure we remap in the right order
                        ranges.append([up - cls.tol, low + cls.tol])
                    else:
                        ranges.append([low - cls.tol, up + cls.tol])
            return ranges

        def offset(range):
            # We first unpad the range by the axis tolerance to make sure that
            # we find the wanted range of the cyclic axis since we padded by the axis tolerance before.
            # Also, it's safer that we find the offset of a value inside the range instead of on the border
            unpadded_range = [range[0] + 1.5 * cls.tol, range[1] - 1.5 * cls.tol]
            cyclic_range = _remap_range_to_axis_range(unpadded_range)
            offset = unpadded_range[0] - cyclic_range[0]
            return offset

        old_find_indices_between = cls.find_indices_between

        def find_indices_between(indexes, low, up, datacube, method=None):
            search_ranges = remap([low, up])
            original_search_ranges = to_intervals([low, up])
            # Find the offsets for each interval in the requested range, which we will need later
            search_ranges_offset = []
            for r in original_search_ranges:
                offset = cls.offset(r)
                search_ranges_offset.append(offset)
            idx_between = []
            for i in range(len(search_ranges)):
                r = search_ranges[i]
                offset = search_ranges_offset[i]
                low = r[0]
                up = r[1]
                indexes_between = old_find_indices_between(indexes, low, up, datacube, method)
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
                            indexes_between[k] = round(indexes_between[k] + offset, int(-math.log10(cls.tol)))
                        idx_between.append(indexes_between[k])
            if offset is not None:
                # Note that we can only do unique if not dealing with time values
                idx_between = unique(idx_between)
            return idx_between

        cls.to_intervals = to_intervals
        cls.remap = remap
        cls.offset = offset
        cls._remap_val_to_axis_range = _remap_val_to_axis_range
        cls.find_indices_between = find_indices_between

    return cls
