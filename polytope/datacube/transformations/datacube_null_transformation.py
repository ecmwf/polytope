from .datacube_transformations import DatacubeAxisTransformation


class DatacubeNullTransformation(DatacubeAxisTransformation):
    def __init__(self, name, mapper_options):
        self.name = name
        self.transformation_options = mapper_options

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


def null(cls):
    if cls.type_change:
        old_find_indexes = cls.find_indexes

        def find_indexes(path, datacube):
            return old_find_indexes(path, datacube)

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            indexes_between_ranges = []
            for indexes in index_ranges:
                indexes_between = [i for i in indexes if low <= i <= up]
                indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.find_indices_between = find_indices_between

    return cls
