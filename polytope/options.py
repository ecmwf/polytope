from conflator import ConfigModel, Conflator
import argparse
from pydantic import ConfigDict
from abc import ABC
from typing import Literal, List, Union, Optional, Dict


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
            axis_config: list[AxisConfig] = []
            compressed_axes_config: list[str] = []
            pre_path: Optional[Dict[str, path_subclasses_union]]

        parser = argparse.ArgumentParser(allow_abbrev=False)
        config_options = Conflator(app_name="polytope", model=Config, cli=False, argparser=parser).load()
        axis_config = None
        compressed_axes_config = None
        pre_path = None
        if options.get("axis_config") or options.get("compressed_axes_config") or options.get("pre_path"):
            config_options = Config(config=options)
            axis_config = config_options.axis_config
            compressed_axes_config = config_options.compressed_axes_config
            pre_path = config_options.pre_path

        return (axis_config, compressed_axes_config, pre_path)

    @staticmethod
    def get_axis_config(options):
        return PolytopeOptions.get_polytope_options(options)[0]

    @staticmethod
    def get_compressed_axes_config(options):
        return PolytopeOptions.get_polytope_options(options)[1]

    @staticmethod
    def get_pre_path(options):
        return PolytopeOptions.get_polytope_options(options)[2]
