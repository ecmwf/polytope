import bisect
import math
from copy import deepcopy
from typing import List

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

        old_find_indexes = cls.find_indexes

        def find_indexes(path, datacube):
            return old_find_indexes(path, datacube)

        old_unmap_path_key = cls.unmap_path_key

        def unmap_path_key(key_value_path, leaf_path, unwanted_path):
            new_values = []
            for value in key_value_path[cls.name]:
                for transform in cls.transformations:
                    if isinstance(transform, DatacubeAxisCyclic):
                        if cls.name == transform.name:
                            new_val = _remap_val_to_axis_range(value)
                            new_values.append(new_val)
            new_values = tuple(new_values)
            key_value_path[cls.name] = new_values
            key_value_path, leaf_path, unwanted_path = old_unmap_path_key(key_value_path, leaf_path, unwanted_path)
            return (key_value_path, leaf_path, unwanted_path)

        old_unmap_to_datacube = cls.unmap_to_datacube

        def unmap_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_to_datacube(path, unmapped_path)
            return (path, unmapped_path)

        old_find_indices_between = cls.find_indices_between

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            update_range()
            indexes_between_ranges = []

            if method != "surrounding" or method != "nearest":
                return old_find_indices_between(index_ranges, low, up, datacube, method)
            else:
                for indexes in index_ranges:
                    if cls.name in datacube.complete_axes:
                        start = indexes.searchsorted(low, "left")
                        end = indexes.searchsorted(up, "right")
                    else:
                        start = bisect.bisect_left(indexes, low)
                        end = bisect.bisect_right(indexes, up)

                    if start - 1 < 0:
                        index_val_found = indexes[-1:][0]
                        indexes_between_ranges.append([index_val_found])
                    if end + 1 > len(indexes):
                        index_val_found = indexes[:2][0]
                        indexes_between_ranges.append([index_val_found])
                    start = max(start - 1, 0)
                    end = min(end + 1, len(indexes))
                    if cls.name in datacube.complete_axes:
                        indexes_between = indexes[start:end].to_list()
                    else:
                        indexes_between = indexes[start:end]
                    indexes_between_ranges.append(indexes_between)
                return indexes_between_ranges

        def offset(range):
            # We first unpad the range by the axis tolerance to make sure that
            # we find the wanted range of the cyclic axis since we padded by the axis tolerance before.
            # Also, it's safer that we find the offset of a value inside the range instead of on the border
            unpadded_range = [range[0] + 1.5 * cls.tol, range[1] - 1.5 * cls.tol]
            cyclic_range = _remap_range_to_axis_range(unpadded_range)
            offset = unpadded_range[0] - cyclic_range[0]
            return offset

        cls.to_intervals = to_intervals
        cls.remap = remap
        cls.offset = offset
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.find_indices_between = find_indices_between
        cls.unmap_path_key = unmap_path_key
        cls._remap_val_to_axis_range = _remap_val_to_axis_range

    return cls
