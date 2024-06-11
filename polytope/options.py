import argparse
from abc import ABC
from typing import Dict, List, Literal, Optional, Union

from conflator import ConfigModel, Conflator
from pydantic import ConfigDict


class PolytopeOptions(ABC):
    @staticmethod
    def get_polytope_options(options):
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
            local: Optional[List[float]] = None

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

        class Config(ConfigModel):
            axis_config: List[AxisConfig] = []
            compressed_axes_config: List[str] = [""]
            pre_path: Optional[Dict[str, path_subclasses_union]] = {}

        parser = argparse.ArgumentParser(allow_abbrev=False)
        config_options = Conflator(app_name="polytope", model=Config, cli=False, argparser=parser).load()
        config_options = Config(
            axis_config=options.get("axis_config", []),
            compressed_axes_config=options.get("compressed_axes_config", [""]),
            pre_path=options.get("pre_path", {}),
        )
        axis_config = config_options.axis_config
        compressed_axes_config = config_options.compressed_axes_config
        pre_path = config_options.pre_path

        return (axis_config, compressed_axes_config, pre_path)