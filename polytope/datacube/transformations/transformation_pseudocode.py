"""from copy import deepcopy


def create_axis_transformations(options, name, values, datacube):
    transformation_options = options["transformation"]
    for transformation_type_key in transformation_options():
        # create transformations
        new_transformation = create_axis_transformation(name, transformation_type_key, transformation_options)
        transformation_axis_names = new_transformation.transformation_axes_final()

        for axis_name in transformation_axis_names:
            #  if axis exists, just add a tag of the transformation, else create axis first and add tag after





            # if there are no transformations for that axis yet, create an empty list of transforms.
            # else, take the old list and append new transformation we are working on
            key_val = datacube.transformation.get(axis_name, [])
            datacube.transformation[axis_name] = key_val
            # the transformation dico keeps track of the type of transformation, not the exact transformations
            # For grid mappers, it keeps track that we have a grid_mapper, but won't know the exact grid map we
            # implement
            datacube.transformation[axis_name].append(new_transformation)
        new_transformation.apply_transformation(name, datacube, values)


def create_axis_transformation(name, transformation_type_key, transformation_options):
    transformation_type = _type_to_datacube_transformation_lookup[transformation_type_key]
    transformation_file_name = _type_to_transformation_file_lookup[transformation_type_key]
    module = import_module("polytope.datacube.transformations.datacube_" + transformation_file_name)
    constructor = getattr(module, transformation_type)
    transformation_type_option = transformation_options[transformation_type_key]
    new_transformation = deepcopy(constructor(name, transformation_type_option))
    new_transformation.name = name
    return new_transformation







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

        new_transformation.name = name
        transformation_axis_names = new_transformation.transformation_axes_final()
        for axis_name in transformation_axis_names:
            # if there are no transformations for that axis yet, create an empty list of transforms.
            # else, take the old list and append new transformation we are working on
            key_val = datacube.transformation.get(axis_name, [])
            datacube.transformation[axis_name] = key_val
            # the transformation dico keeps track of the type of transformation, not the exact transformations
            # For grid mappers, it keeps track that we have a grid_mapper, but won't know the exact grid map we
            # implement
            datacube.transformation[axis_name].append(new_transformation)
        new_transformation.apply_transformation(name, datacube, values)"""