import math
from copy import deepcopy

from ....shapes import ConvexPolytope
from ....utility.geometry import slice_in_two
from ....utility.list_tools import unique
from ..datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisCyclic(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, cyclic_options, datacube=None):
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
        print("WHAT ABOUT HERE")
        print(value)
        value = self._remap_range_to_axis_range([value, value], axis)
        print(value)
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
        if abs(range[0] - range[1]) <= 2 * axis.tol:
            # If we have a range that is just one point, then it should still be counted
            # and so we should take a small interval around it to find values inbetween
            range = [
                self._remap_val_to_axis_range(range[0], axis) - axis.tol,
                self._remap_val_to_axis_range(range[0], axis) + axis.tol,
            ]
            return [range]
        elif axis.range[0] - axis.tol <= range[0] <= axis.range[1] + axis.tol:
            if axis.range[0] - axis.tol <= range[1] <= axis.range[1] + axis.tol:
                # If we are already in the cyclic range, return it
                print("LOOK HERE NOW ACRTUALLY")
                print(range)
                print(range)
                return [range]
        # elif abs(range[0] - range[1]) <= 2 * axis.tol:
        #     # If we have a range that is just one point, then it should still be counted
        #     # and so we should take a small interval around it to find values inbetween
        #     range = [
        #         self._remap_val_to_axis_range(range[0], axis) - axis.tol,
        #         self._remap_val_to_axis_range(range[0], axis) + axis.tol,
        #     ]
        #     return [range]
        range_intervals = self.to_intervals(range, [[]], axis)
        print("WHAT ABOUT HERE ACTUALLY")
        print(range_intervals)
        ranges = []
        for interval in range_intervals:
            if abs(interval[0] - interval[1]) > 0:
                # If the interval is not just a single point, we remap it to the axis range
                range = self._remap_range_to_axis_range([interval[0], interval[1]], axis)
                print("REMAPPED RANGE")
                print(range)
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

    def split_polytope_at_boundary(self, polytope, lon_axis_name, lon_axis):
        """Split a lat/lon polytope at cyclic longitude boundaries and remap each fragment
        into the canonical [axis_lower, axis_upper] range.

        Used so that point-in-polygon queries on unstructured grids work correctly when a
        request polygon straddles the cyclic seam (e.g. lon=[355, 10] on a [0, 360] axis).

        Parameters
        ----------
        polytope : ConvexPolytope
            A 2-D polytope whose axes include *lon_axis_name*.
        lon_axis_name : str
            The name of the longitude axis inside *polytope*.
        lon_axis : DatacubeAxis
            The live axis object (used for ``range`` and ``tol``).

        Returns
        -------
        list[ConvexPolytope]
            One or more polytopes, each with longitude coordinates fully inside
            ``[axis_lower, axis_upper]``.
        """
        self.update_range(lon_axis)
        axis_lower = lon_axis.range[0]
        axis_upper = lon_axis.range[1]
        axis_range = axis_upper - axis_lower

        lon_idx = polytope.axes().index(lon_axis_name)
        lons = [point[lon_idx] for point in polytope.points]
        lon_min = min(lons)
        lon_max = max(lons)

        # Fast-path: polygon already lies inside the canonical range.
        if axis_lower - lon_axis.tol <= lon_min and lon_max <= axis_upper + lon_axis.tol:
            return [polytope]

        # Collect all cyclic boundaries (multiples of axis_range aligned to axis_upper)
        # that fall strictly inside [lon_min, lon_max].
        boundaries = []
        k = math.ceil((lon_min - axis_upper) / axis_range)
        b = axis_upper + k * axis_range
        while b <= lon_max:
            if b > lon_min:
                boundaries.append(b)
            b += axis_range

        def _remap_fragment(frag):
            """Shift all longitude coordinates of *frag* by a uniform offset so that
            they land inside [axis_lower, axis_upper]."""
            frag_lons = [point[lon_idx] for point in frag.points]
            frag_lon_mid = (min(frag_lons) + max(frag_lons)) / 2
            canonical_mid = self._remap_val_to_axis_range(frag_lon_mid, lon_axis)
            offset = canonical_mid - frag_lon_mid
            if offset == 0:
                return frag
            new_points = [[p + offset if i == lon_idx else p for i, p in enumerate(point)] for point in frag.points]
            return ConvexPolytope(
                frag.axes(),
                new_points,
                method=polytope.method,
                k=polytope.k,
                tag=polytope.tag,
            )

        if not boundaries:
            # Polygon lies entirely in one "copy" of the axis range – remap uniformly.
            return [_remap_fragment(polytope)]

        # Split the polygon at each cyclic boundary, then remap each fragment.
        fragments = [polytope]
        for boundary in boundaries:
            new_fragments = []
            for frag in fragments:
                left, right = slice_in_two(frag, boundary, lon_idx)
                if left is not None:
                    new_fragments.append(left)
                if right is not None:
                    new_fragments.append(right)
            fragments = new_fragments

        return [_remap_fragment(frag) for frag in fragments]

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
