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


action_subclasses_union = Union[
    CyclicConfig, MapperConfig, ReverseConfig, TypeChangeConfig, MergeConfig
]


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
    use_catalogue: Optional[bool] = False
    engine_options: Optional[Dict[str, str]] = {}
    dynamic_grid: Optional[bool] = False


class PolytopeOptions(ABC):
    @staticmethod
    def get_polytope_options(options):
        parser = argparse.ArgumentParser(allow_abbrev=False)
        conflator = Conflator(
            app_name="polytope", model=Config, cli=False, argparser=parser, **options
        )
        config_options = conflator.load()

        axis_config = config_options.axis_config
        compressed_axes_config = config_options.compressed_axes_config
        pre_path = config_options.pre_path
        dynamic_grid = config_options.dynamic_grid
        alternative_axes = config_options.alternative_axes
        use_catalogue = config_options.use_catalogue
        engine_options = config_options.engine_options

        if dynamic_grid:
            # TODO: look at the pre-path and query the eccodes function to get the new grid option
            # TODO: then change the grid option inside of the axis_config
            try:
                replaced = replace_grid_config_in_options(config_options, pre_path)
                if replaced:
                    axis_config = config_options.axis_config
            except Exception:
                # Fail silently and continue with original config
                pass
        return (
            axis_config,
            compressed_axes_config,
            pre_path,
            alternative_axes,
            use_catalogue,
            engine_options,
        )


def gridspec_to_grid_config(gridspec, md5hash):
    if gridspec.get("type") == "lambert_conformal":
        mc = MapperConfig(
            name="mapper",
            type="lambert_conformal",
            md5_hash=md5hash,
            is_spherical=gridspec.get("earth_round"),
            radius=gridspec.get("radius"),
            nv=gridspec.get("nv"),
            nx=gridspec.get("nx"),
            ny=gridspec.get("ny"),
            LoVInDegrees=gridspec.get("LoVInDegrees"),
            Dx=gridspec.get("Dx"),
            Dy=gridspec.get("Dy"),
            latFirstInRadians=gridspec.get("latFirstInRadians"),
            lonFirstInRadians=gridspec.get("lonFirstInRadians"),
            LoVInRadians=gridspec.get("LoVInRadians"),
            Latin1InRadians=gridspec.get("Latin1InRadians"),
            Latin2InRadians=gridspec.get("Latin2InRadians"),
            LaDInRadians=gridspec.get("LaDInRadians"),
            axes=["latitude", "longitude"],
        )
        return mc
    return None


def replace_grid_config_in_options(options, req):
    # Lazy import to avoid breaking users without optional switching_grids dependencies
    try:
        from polytope_feature.datacube.switching_grid_helper import lookup_grid_config
    except ImportError:
        # Optional dependencies not available, skip grid replacement
        return False
    
    gridspec, md5hash = lookup_grid_config(req)
    grid_config = gridspec_to_grid_config(gridspec, md5hash)
    if grid_config is not None:
        for axis_conf in options.axis_config:
            for idx, transformation in enumerate(axis_conf.transformations):
                if getattr(transformation, "name", None) == "mapper":
                    axis_conf.transformations[idx] = grid_config
                    return True
    return False
