from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisReverse(DatacubeAxisTransformation):
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
