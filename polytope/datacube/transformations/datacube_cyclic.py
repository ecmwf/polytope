from copy import deepcopy

from datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisCyclic(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, cyclic_options):
        self.name = name
        self.transformation_options = cyclic_options

    def generate_final_transformation(self):
        return self

    def transformation_axes_final(self):
        return [self.name]

    def apply_transformation(self, name, datacube, values):
        # NOTE: we will handle all the cyclicity mapping here instead of in the DatacubeAxis
        # then we can generate just create_standard in the configure_axis at the end
        # Also, in the datacube implementations, we then have to deal with the transformation dico
        # and see if there is a cyclic axis, where we then need to generate the relevant offsets etc
        # from the transformation object

        # OR, we generate a transformation, which we call in a new function create_axis.
        # In create_axis, if we have a cyclic transformation, we generate a cyclic axis, else, a standard one
        pass

    # Cyclic functions

    def to_intervals(self, range):
        axis_lower = self.range[0]
        axis_upper = self.range[1]
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

    def remap_range_to_axis_range(self, range):
        axis_lower = self.range[0]
        axis_upper = self.range[1]
        axis_range = axis_upper - axis_lower
        lower = range[0]
        upper = range[1]
        if lower < axis_lower:
            # In this case we need to calculate the number of loops between the axis lower
            # and the lower to recenter the lower
            loops = int((axis_lower - lower - self.tol) / axis_range)
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

    def remap_val_to_axis_range(self, value):
        return_range = self.remap_range_to_axis_range([value, value])
        return return_range[0]

    def remap(self, range):
        if self.range[0] - self.tol <= range[0] <= self.range[1] + self.tol:
            if self.range[0] - self.tol <= range[1] <= self.range[1] + self.tol:
                # If we are already in the cyclic range, return it
                return [range]
        elif abs(range[0] - range[1]) <= 2 * self.tol:
            # If we have a range that is just one point, then it should still be counted
            # and so we should take a small interval around it to find values inbetween
            range = [
                self.remap_val_to_axis_range(range[0]) - self.tol,
                self.remap_val_to_axis_range(range[0]) + self.tol,
            ]
            return [range]
        range_intervals = self.to_intervals(range)
        ranges = []
        for interval in range_intervals:
            if abs(interval[0] - interval[1]) > 0:
                # If the interval is not just a single point, we remap it to the axis range
                range = self.remap_range_to_axis_range([interval[0], interval[1]])
                up = range[1]
                low = range[0]
                if up < low:
                    # Make sure we remap in the right order
                    ranges.append([up - self.tol, low + self.tol])
                else:
                    ranges.append([low - self.tol, up + self.tol])
        return ranges

    def offset(self, range):
        # We first unpad the range by the axis tolerance to make sure that
        # we find the wanted range of the cyclic axis since we padded by the axis tolerance before.
        # Also, it's safer that we find the offset of a value inside the range instead of on the border
        unpadded_range = [range[0] + 1.5 * self.tol, range[1] - 1.5 * self.tol]
        cyclic_range = self.remap_range_to_axis_range(unpadded_range)
        offset = unpadded_range[0] - cyclic_range[0]
        return offset
