from abc import ABC, abstractmethod, abstractproperty
from copy import deepcopy
from importlib import import_module


class DatacubeAxisTransformation(ABC):

    @staticmethod
    def create_transformation(options, name, values, datacube):

        # transformation options look like
        # "time":{"transformation": { "type" : {"merge" : {"with":"step", "linkers": ["T", "00"]}}}}
        # But the last dictionary can vary and change according to transformation, which can be handled inside the
        # specialised transformations
        transformation_options = options["transformation"]

        # NOTE: we do the following for each transformation of each axis
        for transformation_type_key in transformation_options["type"].keys():
            transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]
            transformation_file_name = _type_to_transformation_file_lookup[transformation_type_key]

            module = import_module("polytope.datacube.datacube_" + transformation_file_name)
            constructor = getattr(module, transformation_type)
            transformation_type_option = transformation_options["type"][transformation_type_key]
            # NOTE: the transformation in the datacube takes in now an option dico like
            # {"with":"step", "linkers": ["T", "00"]}}

            # Here, we keep track of all the transformation objects along with the associated axis within the datacube
            # We generate a transformation dictionary that looks like
            # {"lat": [merger, cyclic], "lon": [mapper, cyclic], etc...}
            new_transformation = deepcopy(constructor(name, transformation_type_option))
            # TODO: instead of adding directly the transformation, could be we have an add_transformation method
            # where each transformation can choose the name that it is assigned to, ie the axis name it is assigned to
            # and then for eg for grid mapper transformation, can have the first axis name in there to make things
            # easier to handle in the datacube
            new_transformation.name = name
            datacube.transformation[name].append(new_transformation)
            new_transformation.apply_transformation(name, datacube, values)

        # TODO: then in subclasses, create init, and inside init, create sub transformation

    @abstractproperty
    def name(self):
        pass

    # TODO: do we need this? to apply transformation to datacube yes...
    @abstractmethod
    def apply_transformation(self, datacube, values):
        pass


_type_to_datacube_transformation_lookup = {"merge": "DatacubeAxisMerger",
                                           "mapper": "DatacubeMapper"}

_type_to_transformation_file_lookup = {"merge" : "merger",
                                       "mapper" : "mappers"}
