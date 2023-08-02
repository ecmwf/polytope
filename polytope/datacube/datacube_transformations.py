from abc import ABC
from importlib import import_module

import numpy as np

from .datacube import configure_datacube_axis


class DatacubeAxisTransformation(ABC):
    @staticmethod
    def create_transformation(options, name, values, datacube):
        # transformation options look like
        # "time":{"transformation": { "type" : {"merge" : {"with":"step", "linker": "00T"}}}}
        # But the last dictionary can vary and change according to transformation, which can be handled inside the
        # specialised transformations
        transformation_options = options["transformation"]
        transformation_type = list(transformation_options["type"].keys())[0]
        transformation_type = _type_to_datacube_transformation_lookup[transformation_type]
        module = import_module("polytope.datacube.datacube_mappers")
        constructor = getattr(module, transformation_type)
        transformation_type_option = transformation_options["type"][transformation_type]
        datacube.transformation = constructor(name, name, transformation_type_option)
        # now need to create an axis for the transformed axis
        # but need to make sure we don't loop infinitely over the transformation option since we did not change
        # the axis name here, unlike in the mappers
        merged_values = datacube.transformation.merged_values(values, datacube)
        axis_options = datacube.axis_options.get(name)
        axis_options.pop("transformation")
        configure_datacube_axis(axis_options, name, merged_values, datacube)


class DatacubeAxisMerger(DatacubeAxisTransformation):
    def __init__(self, name, merge_options):
        self._first_axis = name
        self._second_axis = merge_options["with"]
        self._linker = merge_options["linker"]

    def merged_values(self, values, datacube):
        first_ax_vals = values
        second_ax_name = self._second_axis
        second_ax_vals = datacube.ax_vals(second_ax_name)
        linker = self._linker
        merged_values = []
        for first_val in first_ax_vals:
            for second_val in second_ax_vals:
                merged_values.append(first_val + linker + second_val)
        merged_values = np.array(merged_values)
        return merged_values


_type_to_datacube_transformation_lookup = {"merge": "DatacubeAxisMerger"}
