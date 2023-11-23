from .datacube_transformations import DatacubeAxisTransformation


class DatacubeAxisCyclic(DatacubeAxisTransformation):
    # The transformation here will be to point the old axes to the new cyclic axes

    def __init__(self, name, cyclic_options):
        self.name = name
        self.transformation_options = cyclic_options
        self.range = cyclic_options

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
