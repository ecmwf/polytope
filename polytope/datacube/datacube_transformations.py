from abc import ABC
from importlib import import_module

import numpy as np

from .datacube import configure_datacube_axis


class DatacubeAxisTransformation(ABC):
    @staticmethod
    def create_transformation(options, name, values, datacube):
        # transformation options look like
        # "time":{"transformation": { "type" : {"merge" : {"with":"step", "linkers": ["T", "00"]}}}}
        # But the last dictionary can vary and change according to transformation, which can be handled inside the
        # specialised transformations
        transformation_options = options["transformation"]
        transformation_type_key = list(transformation_options["type"].keys())[0]
        transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]
        module = import_module("polytope.datacube.datacube_transformations")
        constructor = getattr(module, transformation_type)
        transformation_type_option = transformation_options["type"][transformation_type_key]
        datacube.transformation = constructor(name, transformation_type_option)
        # now need to create an axis for the transformed axis
        # but need to make sure we don't loop infinitely over the transformation option since we did not change
        # the axis name here, unlike in the mappers
        merged_values = datacube.transformation.merged_values(values, datacube)
        axis_options = datacube.axis_options.get(name)
        axis_options.pop("transformation")
        configure_datacube_axis(axis_options, name, merged_values, datacube)
        datacube.transformation.finish_transformation(datacube, values)


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options):
        self._first_axis = name
        self._second_axis = merge_options["with"]
        self._linkers = merge_options["linkers"]

    def merged_values(self, values, datacube):
        first_ax_vals = values
        second_ax_name = self._second_axis
        second_ax_vals = datacube.ax_vals(second_ax_name)
        linkers = self._linkers
        merged_values = []
        for first_val in first_ax_vals:
            for second_val in second_ax_vals:
                # TODO: check that the first and second val are strings
                merged_values.append(first_val + linkers[0] + second_val + linkers[1])
        merged_values = np.array(merged_values)
        return merged_values

    def finish_transformation(self, datacube, values):
        datacube.blocked_axes.append(self._second_axis)
        # NOTE: we change the axis values here directly
        datacube.dataarray[self._first_axis] = self.merged_values(values, datacube)


_type_to_datacube_transformation_lookup = {"merge": "DatacubeAxisMerger"}
