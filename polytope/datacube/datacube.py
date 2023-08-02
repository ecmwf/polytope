from abc import ABC, abstractmethod
from typing import Any, List

import xarray as xr

from .datacube_axis import DatacubeAxis
from .index_tree import DatacubePath, IndexTree


class Datacube(ABC):
    @abstractmethod
    def get(self, requests: IndexTree) -> Any:
        """Return data given a set of request trees"""

    @abstractmethod
    def get_mapper(self, axis: str) -> DatacubeAxis:
        """
        Get the type mapper for a subaxis of the datacube given by label
        """

    @abstractmethod
    def get_indices(self, path: DatacubePath, axis: DatacubeAxis, lower: Any, upper: Any) -> List[Any]:
        """
        Given a path to a subset of the datacube, return the discrete indexes which exist between
        two non-discrete values (lower, upper) for a particular axis (given by label)
        If lower and upper are equal, returns the index which exactly matches that value (if it exists)
        e.g. returns integer discrete points between two floats
        """

    @abstractmethod
    def has_index(self, path: DatacubePath, axis: DatacubeAxis, index: Any) -> bool:
        "Given a path to a subset of the datacube, checks if the index exists on that sub-datacube axis"

    @property
    @abstractmethod
    def axes(self) -> dict[str, DatacubeAxis]:
        pass

    @abstractmethod
    def validate(self, axes: List[str]) -> bool:
        """returns true if the input axes can be resolved against the datacube axes"""

    @staticmethod
    def create(datacube, axis_options: dict):
        if isinstance(datacube, (xr.core.dataarray.DataArray, xr.core.dataset.Dataset)):
            from .xarray import XArrayDatacube

            xadatacube = XArrayDatacube(datacube, axis_options=axis_options)
            return xadatacube
        else:
            return datacube

    @abstractmethod
    def ax_vals(self, name: str) -> List:
        pass


def configure_datacube_axis(options, name, values, datacube):
    if name not in datacube.blocked_axes:
        if options == {}:
            DatacubeAxis.create_standard(name, values, datacube)
        if "transformation" in options.keys():
            # the merge options will look like "time": {"merge": {"with":"step", "linker": "00T"}}
            # Need to make sure we do not loop infinitely over this option
            from .datacube_transformations import DatacubeAxisTransformation
            DatacubeAxisTransformation.create_transformation(options, name, values, datacube)
        if "mapper" in options.keys():
            from .datacube_mappers import DatacubeMapper

            DatacubeMapper.create_mapper(options, name, datacube)
        if "cyclic" in options.keys():
            DatacubeAxis.create_cyclic(options, name, values, datacube)
