from abc import ABC, abstractmethod
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
        for transformation_type_key in transformation_options.keys():
            transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]
            transformation_file_name = _type_to_transformation_file_lookup[transformation_type_key]

            module = import_module("polytope.datacube.transformations.datacube_" + transformation_file_name)
            constructor = getattr(module, transformation_type)
            transformation_type_option = transformation_options[transformation_type_key]
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

            # In case there are nested derived classes, want to get the final transformation in our
            # transformation dico
            new_transformation = new_transformation.generate_final_transformation()
            new_transformation.name = name
            datacube.transformation[name].append(new_transformation)
            new_transformation.apply_transformation(name, datacube, values)

    def name(self):
        pass

    def transformation_options(self):
        pass

    @abstractmethod
    def generate_final_transformation(self):
        pass

    # TODO: do we need this? to apply transformation to datacube yes...
    @abstractmethod
    def apply_transformation(self, name, datacube, values):
        pass


_type_to_datacube_transformation_lookup = {"merge": "DatacubeAxisMerger",
                                           "mapper": "DatacubeMapper"}

_type_to_transformation_file_lookup = {"merge" : "merger",
                                       "mapper" : "mappers"}
