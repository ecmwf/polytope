import math
from copy import deepcopy

from ..utility.combinatorics import validate_axes
from .datacube import Datacube, DatacubePath, DatacubeRequestTree
from .datacube_axis import IntAxis


class MockDatacube(Datacube):
    def __init__(self, dimensions):
        assert isinstance(dimensions, dict)

        self.dimensions = dimensions

        self.mappers = {}
        for name in self.dimensions:
            self.mappers[name] = deepcopy(IntAxis())
            self.mappers[name].name = name

        self.stride = {}
        stride_cumulative = 1
        for k, v in reversed(dimensions.items()):
            self.stride[k] = stride_cumulative
            stride_cumulative *= self.dimensions[k]

    def get(self, requests: DatacubeRequestTree):
        # Takes in a datacube and verifies the leaves of the tree are complete
        # (ie it found values for all datacube axis)

        for r in requests.leaves:
            path = r.flatten()
            if len(path.items()) == len(self.dimensions.items()):
                result = 0
                for k, v in path.items():
                    result += v * self.stride[k]

                r.result = result
            else:
                r.remove_branch()

    def get_mapper(self, axis):
        return self.mappers[axis]

    def get_indices(self, path: DatacubePath, axis, lower, upper):
        if lower == upper == math.ceil(lower):
            if lower >= 0:
                return [int(lower)]
            else:
                return []
        lower = max(0, math.ceil(lower))
        upper = min(self.dimensions[axis.name], math.floor(upper) + 1)
        return range(lower, upper)

    def has_index(self, path: DatacubePath, axis, index):
        return True

    @property
    def axes(self):
        return self.mappers

    def validate(self, axes):
        return validate_axes(self.axes, axes)
