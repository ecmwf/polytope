from abc import ABC, abstractmethod
from importlib import import_module

from ..datacube import configure_datacube_axis


class DatacubeAxisTransformation(ABC):
    @staticmethod
    def create_transformation(options, name, values, datacube):
        # transformation options look like
        # "time":{"transformation": { "type" : {"merge" : {"with":"step", "linkers": ["T", "00"]}}}}
        # But the last dictionary can vary and change according to transformation, which can be handled inside the
        # specialised transformations
        transformation_options = options["transformation"]

        # TODO: next line, what happens if there are several transformation options?
        transformation_type_key = list(transformation_options["type"].keys())[0]
        transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]

        # TODO: import from each module individually since they are not all in the same file
        module = import_module("polytope.datacube.datacube_transformations")
        constructor = getattr(module, transformation_type)
        transformation_type_option = transformation_options["type"][transformation_type_key]
        datacube.transformation = constructor(name, transformation_type_option)
        # TODO: then in subclasses, create init, and inside init, create sub transformation
        # and update datacube.transformation

        # now need to create an axis for the transformed axis
        # but need to make sure we don't loop infinitely over the transformation option since we did not change
        # the axis name here, unlike in the mappers

        # TODO: the specifics like merged_values should be stored inside the individual transformations...
        # Really, this is specific to the merger and creating a merger...
        merged_values = datacube.transformation.merged_values(values, datacube)
        axis_options = datacube.axis_options.get(name)
        axis_options.pop("transformation")
        configure_datacube_axis(axis_options, name, merged_values, datacube)

        # TODO: does this really belong in the generic transformation class.
        # TODO: is this even necessary because we are mapping and not creating axes etc?
        datacube.transformation.finish_transformation(datacube, values)

    @abstractmethod
    def finish_transformation(self, datacube, values):
        pass


_type_to_datacube_transformation_lookup = {"merge": "DatacubeAxisMerger",
                                           "mapper": "DatacubeMapper"}
