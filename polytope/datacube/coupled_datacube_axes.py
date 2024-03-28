from abc import ABC


class GroupedAxes(ABC):
    def __init__(self):
        self.transformation = None
        self.grouped_axes = []

    def axes(self):
        return self.grouped_axes


class CoupledAxes(GroupedAxes):
    def __init__(self):
        super.__init__()
        self.removed_axis = None

    def value_combinations(self, artificial_values):
        # TODO: list the possible combinations like [date, time] that come from datetime
        pass
