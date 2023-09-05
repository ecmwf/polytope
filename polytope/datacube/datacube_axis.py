from abc import ABC, abstractmethod, abstractproperty
from copy import deepcopy
from typing import Any, List

import numpy as np
import pandas as pd


def cyclic(cls):
    if cls.is_cyclic:
        from .transformations.datacube_cyclic import DatacubeAxisCyclic

        def update_range():
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisCyclic):
                    transformation = transform
                    cls.range = transformation.range

        def to_intervals(range):
            update_range()
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

        old_unmap_total_path_to_datacube = cls.unmap_total_path_to_datacube

        def unmap_total_path_to_datacube(path, unmapped_path):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisCyclic):
                    transformation = transform
                    if cls.name == transformation.name:
                        old_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        new_val = _remap_val_to_axis_range(old_val)
                        path[cls.name] = new_val
            (path, unmapped_path) = old_unmap_total_path_to_datacube(path, unmapped_path)
            return (path, unmapped_path)

        old_unmap_to_datacube = cls.unmap_to_datacube

        def unmap_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_to_datacube(path, unmapped_path)
            return (path, unmapped_path)

        old_find_indices_between = cls.find_indices_between

        def find_indices_between(index_ranges, low, up, datacube, offset, method=None):
            update_range()
            range_length = cls.range[1] - cls.range[0]
            indexes_between_ranges = []

            if method != "surrounding":
                return old_find_indices_between(index_ranges, low, up, datacube, method, offset)

            if offset != 0:
                # NOTE that if the offset is not 0, then we need to recenter the low and up
                # values to be within the datacube range
                new_offset = 0
                if low <= cls.range[0] + cls.tol:
                    while low >= cls.range[0] - cls.tol:
                        low = low - range_length
                        new_offset -= range_length
                        up = up - range_length
                if method == "surrounding":
                    for indexes in index_ranges:
                        if cls.name in datacube.complete_axes:
                            start = indexes.searchsorted(low, "left")
                            end = indexes.searchsorted(up, "right")
                            if start-1 < 0:  # NOTE TODO: here the boundaries will not necessarily be 0 or len(indexes)
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[-1:][0]
                                indexes_between_before = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_before)
                            if end+1 > len(indexes):
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[:1][0]
                                indexes_between_after = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_after)
                            start = max(start-1, 0)
                            end = min(end+1, len(indexes))
                            indexes_between = indexes[start:end].to_list()
                            indexes_between = [i - new_offset for i in indexes_between]
                            indexes_between_ranges.append(indexes_between)
                        else:
                            start = indexes.index(low)
                            end = indexes.index(up)
                            if start-1 < 0:
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[-1:][0]
                                indexes_between_before = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_before)
                            if end+1 > len(indexes):
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[:1][0]
                                indexes_between_after = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_after)
                            start = max(start-1, 0)
                            end = min(end+1, len(indexes))
                            indexes_between = indexes[start:end]
                            indexes_between_ranges.append(indexes_between)
                    return indexes_between_ranges
                else:
                    return old_find_indices_between(index_ranges, low, up, datacube, method, offset)

            else:
                # If the offset is 0, then the first value found on the left has an offset of range_length
                new_offset = 0
                if method == "surrounding":
                    for indexes in index_ranges:
                        if cls.name in datacube.complete_axes:
                            start = indexes.searchsorted(low, "left")
                            end = indexes.searchsorted(up, "right")
                            if start-1 < 0:  # NOTE TODO: here the boundaries will not necessarily be 0 or len(indexes)
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[-1:][0]
                                new_offset = -range_length
                                indexes_between_before = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_before)
                            if end+1 > len(indexes):
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[:1][0]
                                indexes_between_after = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_after)
                            start = max(start-1, 0)
                            end = min(end+1, len(indexes))
                            indexes_between = indexes[start:end].to_list()
                            indexes_between = [i - new_offset for i in indexes_between]
                            indexes_between_ranges.append(indexes_between)
                        else:
                            start = indexes.index(low)
                            end = indexes.index(up)
                            if start-1 < 0:
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[-1:][0]
                                indexes_between_before = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_before)
                            if end+1 > len(indexes):
                                start_offset_indicator = "need_offset"
                                index_val_found = indexes[:1][0]
                                indexes_between_after = [start_offset_indicator, new_offset, index_val_found]
                                indexes_between_ranges.append(indexes_between_after)
                            start = max(start-1, 0)
                            end = min(end+1, len(indexes))
                            indexes_between = indexes[start:end]
                            indexes_between_ranges.append(indexes_between)
                    return indexes_between_ranges
                else:
                    return old_find_indices_between(index_ranges, low, up, datacube, method, offset)

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
        cls.unmap_total_path_to_datacube = unmap_total_path_to_datacube
        cls.find_indices_between = find_indices_between

    return cls


def mapper(cls):
    from .transformations.datacube_mappers import DatacubeMapper

    if cls.has_mapper:
        def find_indexes(path, datacube):
            # first, find the relevant transformation object that is a mapping in the cls.transformation dico
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name == transformation._mapped_axes()[0]:
                        return transformation.first_axis_vals()
                    if cls.name == transformation._mapped_axes()[1]:
                        first_val = path[transformation._mapped_axes()[0]]
                        return transformation.second_axis_vals(first_val)

        old_unmap_to_datacube = cls.unmap_to_datacube

        def unmap_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name == transformation._mapped_axes()[0]:
                        # if we are on the first axis, then need to add the first val to unmapped_path
                        first_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        if cls.name not in unmapped_path:
                            # if for some reason, the unmapped_path already has the first axis val, then don't update
                            unmapped_path[cls.name] = first_val
                    if cls.name == transformation._mapped_axes()[1]:
                        # if we are on the second axis, then the val of the first axis is stored
                        # inside unmapped_path so can get it from there
                        second_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        first_val = unmapped_path.get(transformation._mapped_axes()[0], None)
                        unmapped_path.pop(transformation._mapped_axes()[0], None)
                        # if the first_val was not in the unmapped_path, then it's still in path
                        if first_val is None:
                            first_val = path.get(transformation._mapped_axes()[0], None)
                            path.pop(transformation._mapped_axes()[0], None)
                        if first_val is not None and second_val is not None:
                            unmapped_idx = transformation.unmap(first_val, second_val)
                            unmapped_path[transformation.old_axis] = unmapped_idx
            return (path, unmapped_path)

        old_unmap_total_path_to_datacube = cls.unmap_total_path_to_datacube

        def unmap_total_path_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_total_path_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name == transformation._mapped_axes()[0]:
                        # if we are on the first axis, then need to add the first val to unmapped_path
                        first_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        if cls.name not in unmapped_path:
                            # if for some reason, the unmapped_path already has the first axis val, then don't update
                            unmapped_path[cls.name] = first_val
                    if cls.name == transformation._mapped_axes()[1]:
                        # if we are on the second axis, then the val of the first axis is stored
                        # inside unmapped_path so can get it from there
                        second_val = path.get(cls.name, None)
                        path.pop(cls.name, None)
                        first_val = unmapped_path.get(transformation._mapped_axes()[0], None)
                        unmapped_path.pop(transformation._mapped_axes()[0], None)
                        # if the first_val was not in the unmapped_path, then it's still in path
                        if first_val is None:
                            first_val = path.get(transformation._mapped_axes()[0], None)
                            path.pop(transformation._mapped_axes()[0], None)
                        if first_val is not None and second_val is not None:
                            unmapped_idx = transformation.unmap(first_val, second_val)
                            unmapped_path[transformation.old_axis] = unmapped_idx
            return (path, unmapped_path)

        def remap_to_requested(path, unmapped_path):
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, offset, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeMapper):
                    transformation = transform
                    if cls.name in transformation._mapped_axes():
                        for idxs in index_ranges:
                            if method == "surrounding":
                                start = idxs.index(low)
                                end = idxs.index(up)
                                start = max(start-1, 0)
                                end = min(end+1, len(idxs))
                                # indexes_between = [i for i in indexes if low <= i <= up]
                                indexes_between = idxs[start:end]
                                indexes_between_ranges.append(indexes_between)
                            else:
                                indexes_between = [i for i in idxs if low <= i <= up]
                                indexes_between_ranges.append(indexes_between)
                            # indexes_between = [i for i in idxs if low <= i <= up]
                            # indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        old_remap = cls.remap

        def remap(range):
            return old_remap(range)

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.remap_to_requested = remap_to_requested
        cls.find_indices_between = find_indices_between
        cls.unmap_total_path_to_datacube = unmap_total_path_to_datacube

    return cls


def merge(cls):
    from .transformations.datacube_merger import DatacubeAxisMerger

    if cls.has_merger:
        def find_indexes(path, datacube):
            # first, find the relevant transformation object that is a mapping in the cls.transformation dico
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name == transformation._first_axis:
                        return transformation.merged_values(datacube)

        old_unmap_total_path_to_datacube = cls.unmap_total_path_to_datacube

        def unmap_total_path_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_total_path_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name == transformation._first_axis:
                        old_val = path.get(cls.name, None)
                        (first_val, second_val) = transformation.unmerge(old_val)
                        path.pop(cls.name, None)
                        path[transformation._first_axis] = first_val
                        path[transformation._second_axis] = second_val
            return (path, unmapped_path)

        old_unmap_to_datacube = cls.unmap_to_datacube

        def unmap_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name == transformation._first_axis:
                        old_val = path.get(cls.name, None)
                        (first_val, second_val) = transformation.unmerge(old_val)
                        path.pop(cls.name, None)
                        path[transformation._first_axis] = first_val
                        path[transformation._second_axis] = second_val
            return (path, unmapped_path)

        def remap_to_requested(path, unmapped_path):
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, offset, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisMerger):
                    transformation = transform
                    if cls.name in transformation._mapped_axes():
                        for indexes in index_ranges:
                            if method == "surrounding":
                                start = indexes.index(low)
                                end = indexes.index(up)
                                start = max(start-1, 0)
                                end = min(end+1, len(indexes))
                                # indexes_between = [i for i in indexes if low <= i <= up]
                                indexes_between = indexes[start:end]
                                indexes_between_ranges.append(indexes_between)
                            else:
                                indexes_between = [i for i in indexes if low <= i <= up]
                                indexes_between_ranges.append(indexes_between)
                            # indexes_between = [i for i in indexes if low <= i <= up]
                            # indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.remap_to_requested = remap_to_requested
        cls.find_indices_between = find_indices_between
        cls.unmap_total_path_to_datacube = unmap_total_path_to_datacube

    return cls


def reverse(cls):
    from .transformations.datacube_reverse import DatacubeAxisReverse

    if cls.reorder:
        def find_indexes(path, datacube):
            # first, find the relevant transformation object that is a mapping in the cls.transformation dico
            subarray = datacube.dataarray.sel(path, method="nearest")
            unordered_indices = datacube.datacube_natural_indexes(cls, subarray)
            if cls.name in datacube.complete_axes:
                ordered_indices = unordered_indices.sort_values()
            else:
                ordered_indices = unordered_indices
            return ordered_indices

        def unmap_to_datacube(path, unmapped_path):
            return (path, unmapped_path)

        def remap_to_requested(path, unmapped_path):
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, offset, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisReverse):
                    transformation = transform
                    if cls.name == transformation.name:
                        for indexes in index_ranges:
                            if cls.name in datacube.complete_axes:
                                # Find the range of indexes between lower and upper
                                # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
                                # Assumes the indexes are already sorted (could sort to be sure) and monotonically
                                # increasing
                                if method == "surrounding":
                                    start = indexes.searchsorted(low, "left")
                                    end = indexes.searchsorted(up, "right")
                                    start = max(start-1, 0)
                                    end = min(end+1, len(indexes))
                                    indexes_between = indexes[start:end].to_list()
                                    indexes_between_ranges.append(indexes_between)
                                else:
                                    start = indexes.searchsorted(low, "left")
                                    end = indexes.searchsorted(up, "right")
                                    indexes_between = indexes[start:end].to_list()
                                    indexes_between_ranges.append(indexes_between)
                            else:
                                if method == "surrounding":
                                    start = indexes.index(low)
                                    end = indexes.index(up)
                                    start = max(start-1, 0)
                                    end = min(end+1, len(indexes))
                                    # indexes_between = [i for i in indexes if low <= i <= up]
                                    indexes_between = indexes[start:end]
                                    indexes_between_ranges.append(indexes_between)
                                else:
                                    indexes_between = [i for i in indexes if low <= i <= up]
                                    indexes_between_ranges.append(indexes_between)
                            # if method == "surrounding":
                            #     start = indexes.index(low)
                            #     end = indexes.index(up)
                            #     start = max(start-1, 0)
                            #     end = min(end+1, len(indexes))
                            #     # indexes_between = [i for i in indexes if low <= i <= up]
                            #     indexes_between = indexes[start:end]
                            #     indexes_between_ranges.append(indexes_between)
                            # else:
                            #     indexes_between = [i for i in indexes if low <= i <= up]
                            #     indexes_between_ranges.append(indexes_between)
                            # indexes_between = [i for i in indexes if low <= i <= up]
                            # indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.remap_to_requested = remap_to_requested
        cls.find_indices_between = find_indices_between

    return cls


def type_change(cls):
    from .transformations.datacube_type_change import DatacubeAxisTypeChange

    if cls.type_change:

        old_find_indexes = cls.find_indexes

        def find_indexes(path, datacube):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        original_vals = old_find_indexes(path, datacube)
                        return transformation.change_val_type(cls.name, original_vals)

        old_unmap_total_path_to_datacube = cls.unmap_total_path_to_datacube

        def unmap_total_path_to_datacube(path, unmapped_path):
            (path, unmapped_path) = old_unmap_total_path_to_datacube(path, unmapped_path)
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        changed_val = path.get(cls.name, None)
                        unchanged_val = transformation.make_str(changed_val)
                        if cls.name in path:
                            path.pop(cls.name, None)
                            unmapped_path[cls.name] = unchanged_val
            return (path, unmapped_path)

        def unmap_to_datacube(path, unmapped_path):
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        changed_val = path.get(cls.name, None)
                        unchanged_val = transformation.make_str(changed_val)
                        if cls.name in path:
                            path.pop(cls.name, None)
                            unmapped_path[cls.name] = unchanged_val
            return (path, unmapped_path)

        def remap_to_requested(path, unmapped_path):
            return (path, unmapped_path)

        def find_indices_between(index_ranges, low, up, datacube, offset, method=None):
            # TODO: add method for snappping
            indexes_between_ranges = []
            for transform in cls.transformations:
                if isinstance(transform, DatacubeAxisTypeChange):
                    transformation = transform
                    if cls.name == transformation.name:
                        for indexes in index_ranges:
                            if method == "surrounding":
                                start = indexes.index(low)
                                end = indexes.index(up)
                                start = max(start-1, 0)
                                end = min(end+1, len(indexes))
                                # indexes_between = [i for i in indexes if low <= i <= up]
                                indexes_between = indexes[start:end]
                                indexes_between_ranges.append(indexes_between)
                            else:
                                indexes_between = [i for i in indexes if low <= i <= up]
                                indexes_between_ranges.append(indexes_between)
                            # indexes_between = [i for i in indexes if low <= i <= up]
                            # indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.unmap_to_datacube = unmap_to_datacube
        cls.remap_to_requested = remap_to_requested
        cls.find_indices_between = find_indices_between
        cls.unmap_total_path_to_datacube = unmap_total_path_to_datacube

    return cls


class DatacubeAxis(ABC):
    is_cyclic = False
    has_mapper = False
    has_merger = False
    reorder = False
    type_change = False

    def update_axis(self):
        if self.is_cyclic:
            self = cyclic(self)
        return self

    @abstractproperty
    def name(self) -> str:
        pass

    @abstractproperty
    def tol(self) -> Any:
        pass

    @abstractproperty
    def range(self) -> List[Any]:
        pass

    # Convert from user-provided value to CONTINUOUS type (e.g. float, pd.timestamp)
    @abstractmethod
    def parse(self, value: Any) -> Any:
        pass

    # Convert from CONTINUOUS type to FLOAT
    @abstractmethod
    def to_float(self, value: Any) -> float:
        pass

    # Convert from FLOAT type to CONTINUOUS type
    @abstractmethod
    def from_float(self, value: float) -> Any:
        pass

    def serialize(self, value: Any) -> Any:
        pass

    def to_intervals(self, range):
        return [range]

    def remap(self, range: List) -> Any:
        return [range]

    def unmap_to_datacube(self, path, unmapped_path):
        return (path, unmapped_path)

    def find_indexes(self, path, datacube):
        unmapped_path = {}
        path_copy = deepcopy(path)
        for key in path_copy:
            axis = datacube._axes[key]
            (path, unmapped_path) = axis.unmap_to_datacube(path, unmapped_path)
        subarray = datacube.select(path, unmapped_path)
        return datacube.datacube_natural_indexes(self, subarray)

    def offset(self, value):
        return 0

    def unmap_total_path_to_datacube(self, path, unmapped_path):
        return (path, unmapped_path)

    def remap_to_requeest(path, unmapped_path):
        return (path, unmapped_path)

    def find_indices_between(self, index_ranges, low, up, datacube, offset, method=None):
        # TODO: add method for snappping
        indexes_between_ranges = []
        for indexes in index_ranges:
            if self.name in datacube.complete_axes:
                # Find the range of indexes between lower and upper
                # https://pandas.pydata.org/docs/reference/api/pandas.Index.searchsorted.html
                # Assumes the indexes are already sorted (could sort to be sure) and monotonically increasing
                if method == "surrounding":
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    start = max(start-1, 0)
                    end = min(end+1, len(indexes))
                    indexes_between = indexes[start:end].to_list()
                    indexes_between_ranges.append(indexes_between)
                else:
                    start = indexes.searchsorted(low, "left")
                    end = indexes.searchsorted(up, "right")
                    indexes_between = indexes[start:end].to_list()
                    indexes_between_ranges.append(indexes_between)
            else:
                if method == "surrounding":
                    start = indexes.index(low)
                    end = indexes.index(up)
                    start = max(start-1, 0)
                    end = min(end+1, len(indexes))
                    # indexes_between = [i for i in indexes if low <= i <= up]
                    indexes_between = indexes[start:end]
                    indexes_between_ranges.append(indexes_between)
                else:
                    indexes_between = [i for i in indexes if low <= i <= up]
                    indexes_between_ranges.append(indexes_between)
        return indexes_between_ranges

    @staticmethod
    def create_standard(name, values, datacube):
        values = np.array(values)
        DatacubeAxis.check_axis_type(name, values)
        datacube._axes[name] = deepcopy(_type_to_axis_lookup[values.dtype.type])
        datacube._axes[name].name = name
        datacube.axis_counter += 1

    @staticmethod
    def check_axis_type(name, values):
        # NOTE: The values here need to be a numpy array which has a dtype attribute
        if values.dtype.type not in _type_to_axis_lookup:
            raise ValueError(f"Could not create a mapper for index type {values.dtype.type} for axis {name}")


@reverse
@cyclic
@mapper
@type_change
class IntDatacubeAxis(DatacubeAxis):
    name = None
    tol = 1e-12
    range = None
    transformations = []
    type = 0

    def parse(self, value: Any) -> Any:
        return float(value)

    def to_float(self, value):
        return float(value)

    def from_float(self, value):
        return float(value)

    def serialize(self, value):
        return value


@reverse
@cyclic
@mapper
@type_change
class FloatDatacubeAxis(DatacubeAxis):
    name = None
    tol = 1e-12
    range = None
    transformations = []
    type = 0.

    def parse(self, value: Any) -> Any:
        return float(value)

    def to_float(self, value):
        return float(value)

    def from_float(self, value):
        return float(value)

    def serialize(self, value):
        return value


@merge
class PandasTimestampDatacubeAxis(DatacubeAxis):
    name = None
    tol = 1e-12
    range = None
    transformations = []
    type = pd.Timestamp("2000-01-01T00:00:00")

    def parse(self, value: Any) -> Any:
        if isinstance(value, np.str_):
            value = str(value)
        return pd.Timestamp(value)

    def to_float(self, value: pd.Timestamp):
        if isinstance(value, np.datetime64):
            return float((value - np.datetime64("1970-01-01T00:00:00")).astype("int"))
        else:
            return float(value.value / 10**9)

    def from_float(self, value):
        return pd.Timestamp(int(value), unit="s")

    def serialize(self, value):
        return str(value)

    def offset(self, value):
        return None


@merge
class PandasTimedeltaDatacubeAxis(DatacubeAxis):
    name = None
    tol = 1e-12
    range = None
    transformations = []
    type = np.timedelta64(0, "s")

    def parse(self, value: Any) -> Any:
        if isinstance(value, np.str_):
            value = str(value)
        return pd.Timedelta(value)

    def to_float(self, value: pd.Timedelta):
        if isinstance(value, np.timedelta64):
            return value.astype("timedelta64[s]").astype(int)
        else:
            return float(value.value / 10**9)

    def from_float(self, value):
        return pd.Timedelta(int(value), unit="s")

    def serialize(self, value):
        return str(value)

    def offset(self, value):
        return None


@type_change
class UnsliceableDatacubeAxis(DatacubeAxis):
    name = None
    tol = float("NaN")
    range = None
    transformations = []

    def parse(self, value: Any) -> Any:
        return value

    def to_float(self, value: pd.Timedelta):
        raise TypeError("Tried to slice unsliceable axis")

    def from_float(self, value):
        raise TypeError("Tried to slice unsliceable axis")

    def serialize(self, value):
        raise TypeError("Tried to slice unsliceable axis")


_type_to_axis_lookup = {
    pd.Int64Dtype: IntDatacubeAxis(),
    pd.Timestamp: PandasTimestampDatacubeAxis(),
    np.int64: IntDatacubeAxis(),
    np.datetime64: PandasTimestampDatacubeAxis(),
    np.timedelta64: PandasTimedeltaDatacubeAxis(),
    np.float64: FloatDatacubeAxis(),
    np.str_: UnsliceableDatacubeAxis(),
    str: UnsliceableDatacubeAxis(),
    np.object_: UnsliceableDatacubeAxis(),
}
