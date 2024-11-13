from abc import ABC
from typing import Dict, List, Literal, Optional, Union

from conflator import ConfigModel
from pydantic import ConfigDict


class TransformationConfig(ConfigModel):
    model_config = ConfigDict(extra="forbid")
    name: str = ""


class CyclicConfig(TransformationConfig):
    name: Literal["cyclic"]
    range: List[float] = [0]


class MapperConfig(TransformationConfig):
    name: Literal["mapper"]
    type: str = ""
    resolution: Union[int, List[int]] = 0
    axes: List[str] = [""]
    md5_hash: Optional[str] = None
    local: Optional[List[float]] = None
    axis_reversed: Optional[Dict[str, bool]] = None


class ReverseConfig(TransformationConfig):
    name: Literal["reverse"]
    is_reverse: bool = False


class TypeChangeConfig(TransformationConfig):
    name: Literal["type_change"]
    type: str = "int"


class MergeConfig(TransformationConfig):
    name: Literal["merge"]
    other_axis: str = ""
    linkers: List[str] = [""]


action_subclasses_union = Union[CyclicConfig, MapperConfig, ReverseConfig, TypeChangeConfig, MergeConfig]


class AxisConfig(ConfigModel):
    axis_name: str = ""
    transformations: list[action_subclasses_union]


path_subclasses_union = Union[str, int, float]


class GribJumpAxesConfig(ConfigModel):
    axis_name: str = ""
    values: List[str] = [""]


class Config(ConfigModel):
    axis_config: List[AxisConfig] = []
    compressed_axes_config: List[str] = [""]
    pre_path: Optional[Dict[str, path_subclasses_union]] = {}
    alternative_axes: List[GribJumpAxesConfig] = []


class PolytopeOptions(ABC):
    @staticmethod
    def get_polytope_options(options):
        config_options = Config.model_validate(options)

        axis_config = config_options.axis_config
        compressed_axes_config = config_options.compressed_axes_config
        pre_path = config_options.pre_path
        alternative_axes = config_options.alternative_axes

        return (axis_config, compressed_axes_config, pre_path, alternative_axes)
