import argparse
from abc import ABC
from typing import Dict, List, Literal, Optional, Tuple, Union

from conflator import ConfigModel, Conflator
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
    resolution: Optional[Union[int, List[int]]] = 0
    axes: List[str] = [""]
    md5_hash: Optional[str] = None
    local: Optional[List[float]] = None
    axis_reversed: Optional[Dict[str, bool]] = None
    is_spherical: Optional[bool] = None
    radius: Optional[float] = None
    earthMinorAxisInMetres: Optional[float] = None
    earthMajorAxisInMetres: Optional[float] = None
    nv: Optional[int] = None
    nx: Optional[int] = None
    ny: Optional[int] = None
    LoVInDegrees: Optional[float] = None
    Dx: Optional[float] = None
    Dy: Optional[float] = None
    latFirstInRadians: Optional[float] = None
    lonFirstInRadians: Optional[float] = None
    LoVInRadians: Optional[float] = None
    Latin1InRadians: Optional[float] = None
    Latin2InRadians: Optional[float] = None
    LaDInRadians: Optional[float] = None
    # points: Optional[List[List[float]]] = None
    points: Optional[List[Tuple[float, float]]] = None
    uuid: Optional[str] = None


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
    alternative_axes: Optional[List[GribJumpAxesConfig]] = []
    grid_online_path: Optional[str] = ""
    grid_local_directory: Optional[str] = ""
    use_catalogue: Optional[bool] = False
    engine_options: Optional[Dict[str, str]] = {}


class PolytopeOptions(ABC):
    @staticmethod
    def get_polytope_options(options):
        parser = argparse.ArgumentParser(allow_abbrev=False)
        conflator = Conflator(app_name="polytope", model=Config, cli=False, argparser=parser, **options)
        config_options = conflator.load()

        axis_config = config_options.axis_config
        compressed_axes_config = config_options.compressed_axes_config
        pre_path = config_options.pre_path
        alternative_axes = config_options.alternative_axes
        grid_online_path = config_options.grid_online_path
        grid_local_directory = config_options.grid_local_directory
        use_catalogue = config_options.use_catalogue
        engine_options = config_options.engine_options
        return (
            axis_config,
            compressed_axes_config,
            pre_path,
            alternative_axes,
            grid_online_path,
            grid_local_directory,
            use_catalogue,
            engine_options,
        )
