from typing import Dict, List, Union

from conflator import ConfigModel, Conflator

from .shapes import ConvexPolytope
from .utility.exceptions import AxisOverdefinedError

from pydantic import validator

from typing import Literal, Union, List

import pytest
import yaml
from pydantic import validator
from pydantic import ConfigDict

from conflator import ConfigModel, Conflator


class Request:
    """Encapsulates a request for data"""

    def __init__(self, *shapes):
        self.shapes = list(shapes)
        self.check_axes()

    def check_axes(self):
        """Check that all axes are defined by the combination of shapes, and that they are defined only once"""
        defined_axes = []

        for shape in self.shapes:
            for axis in shape.axes():
                if axis not in defined_axes:
                    defined_axes.append(axis)
                else:
                    raise AxisOverdefinedError(axis)

    def polytopes(self):
        """Returns the representation of the request as polytopes"""
        polytopes = []
        for shape in self.shapes:
            polytopes.extend(shape.polytope())
        return polytopes

    def __repr__(self):
        return_str = ""
        for shape in self.shapes:
            return_str += shape.__repr__() + "\n"
        return return_str


class Polytope:
    def __init__(self, datacube, engine=None, axis_options=None, datacube_options=None):
        from .datacube import Datacube
        from .engine import Engine

        if axis_options is None:
            axis_options = {}
        if datacube_options is None:
            datacube_options = {}

        # # TODO: not sure this is what we want?
        # conflator = Conflator(app_name="polytope", model=DatacubeConfig)
        # self.datacube_config = conflator.load()
        # self.datacube_config.config = axis_options

        # class TransformationConfig(ConfigModel):
        #     model_config = ConfigDict(extra="forbid")
        #     name: str = ""

        # class CyclicConfig(TransformationConfig):
        #     name: Literal["cyclic"]
        #     range: List[int] = [0]

        # class MapperConfig(TransformationConfig):
        #     name: Literal["mapper"]
        #     type: str = ""
        #     resolution: int = 0
        #     axes: List[str] = [""]

        # class ReverseConfig(TransformationConfig):
        #     name: Literal["reverse"]
        #     is_reverse: bool = False

        # class TypeChangeConfig(TransformationConfig):
        #     name: Literal["type_change"]
        #     type: str = "int"

        # class MergeConfig(TransformationConfig):
        #     name: Literal["merge"]
        #     other_axis: str = ""
        #     linkers: List[str] = [""]

        # action_subclasses_union = Union[CyclicConfig, MapperConfig, ReverseConfig, TypeChangeConfig, MergeConfig]

        # class AxisConfig(ConfigModel):
        #     axis_name: str = ""
        #     transformations: list[action_subclasses_union]

        #     # @validator("axis_name")
        #     # def check_size(cls, v):
        #     #     assert v in self.datacube._axes.keys()
        #     #     return v

        # class Config(ConfigModel):
        #     config: list[AxisConfig]

        # axis_config = Conflator(app_name="polytope", model=Config, cli=False, **axis_options).load()

        self.datacube = Datacube.create(datacube, axis_options)
        self.engine = engine if engine is not None else Engine.default()

    def slice(self, polytopes: List[ConvexPolytope]):
        """Low-level API which takes a polytope geometry object and uses it to slice the datacube"""
        return self.engine.extract(self.datacube, polytopes)

    def retrieve(self, request: Request, method="standard"):
        """Higher-level API which takes a request and uses it to slice the datacube"""
        request_tree = self.engine.extract(self.datacube, request.polytopes())
        self.datacube.get(request_tree)
        return request_tree

    # class TransformationConfig(ConfigModel):
    #     model_config = ConfigDict(extra="forbid")
    #     name: str = ""

    # class CyclicConfig(TransformationConfig):
    #     name: Literal["cyclic"]
    #     range: List[int] = [0]

    # class MapperConfig(TransformationConfig):
    #     name: Literal["mapper"]
    #     type: str = ""
    #     resolution: int = 0
    #     axes: List[str] = [""]

    # class ReverseConfig(TransformationConfig):
    #     name: Literal["reverse"]
    #     is_reverse: bool = False

    # class TypeChangeConfig(TransformationConfig):
    #     name: Literal["type_change"]
    #     type: str = "int"

    # class MergeConfig(TransformationConfig):
    #     name: Literal["merge"]
    #     other_axis: str = ""
    #     linkers: List[str] = [""]

    # action_subclasses_union = Union[CyclicConfig, MapperConfig, ReverseConfig, TypeChangeConfig, MergeConfig]

    # def get_datacube_axes(self):
    #     return self.datacube._axes.keys()

    # class AxisConfig(ConfigModel):
    #     axis_name: str = ""
    #     transformations: list["Polytope.action_subclasses_union"]

    #     @validator("axis_name")
    #     def check_size(cls, v):
    #         assert v in self.datacube._axes.keys()
    #         return v

    # class Config(ConfigModel):
    #     config: list["Polytope.AxisConfig"]


# class TransformConfig(ConfigModel):
#     name: str = ""

# class TypeChangeTransformation(TransformConfig):
#     name: str = "type_change"
#     type: str = "int"

# class AxisConfig(ConfigModel):
#     transform_name: str = ""
#     axis_name: str = ""
#     transform_config: TransformConfig = TransformConfig()


# # class SubDatacubeConfig(ConfigModel):
# #     # TODO: need to change this to make it fit the actual options with the different transformations
# #     # TODO: could validate the subtypes options with the name stored in the dictionary??
# #     axis_config: Dict[str, Union[Dict, str]] = {"": {}}


# # class DatacubeConfig(ConfigModel):
# #     # config: Dict[str, SubDatacubeConfig] = {"", SubDatacubeConfig()}
# #     config: Dict[str, Union(TypeChangeOptions, CyclicOptions, MapperOptions, MergerOptions, ReverseOptions)] = {"", SubDatacubeConfig()}

# #     @validator("config")
# #     def check_size(cls, v):
# #         assert len(v) == 1
# #         return v
    
# #     # TODO: validate the keys of the config with the datacube...


# # class TypeChangeOptions(ConfigModel):
# #     name: str = "type_change"
# #     type: str = ""


# # class CyclicOptions(ConfigModel):
# #     name: str = "cyclic"
# #     range: List = []


# # class MapperOptions(ConfigModel):
# #     # TODO: Think about this? How can we assign the sub-dictionary items to the mapper options??
# #     options: Dict
# #     pass


# # class SubMapperOptions(ConfigModel):
# #     pass


# # class MergerOptions(ConfigModel):
# #     pass


# # class ReverseOptions(ConfigModel):
# #     pass
