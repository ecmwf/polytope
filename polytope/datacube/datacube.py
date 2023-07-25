from abc import ABC, abstractmethod
from typing import Any, List

import xarray as xr

from .datacube_axis import DatacubeAxis
from .datacube_request_tree import DatacubePath, IndexTree


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
    def create(datacube, options: dict):
        if isinstance(datacube, (xr.core.dataarray.DataArray, xr.core.dataset.Dataset)):
            from .xarray import XArrayDatacube

            xadatacube = XArrayDatacube(datacube, axis_options=axis_options)
            return xadatacube
