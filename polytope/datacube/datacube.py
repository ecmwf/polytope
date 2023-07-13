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
    def get_mapper(self, axis) -> DatacubeAxis:
        """
        Get the type mapper for a subaxis of the datacube given by label
        """

    @abstractmethod
    def get_indices(self, path: DatacubePath, axis: str, lower: Any, upper: Any) -> List:
        """
        Given a path to a subset of the datacube, return the discrete indexes which exist between
        two non-discrete values (lower, upper) for a particular axis (given by label)
        If lower and upper are equal, returns the index which exactly matches that value (if it exists)
        e.g. returns integer discrete points between two floats
        """

    @abstractmethod
    def has_index(self, path: DatacubePath, axis, index) -> bool:
        "Given a path to a subset of the datacube, checks if the index exists on that sub-datacube axis"

    @property
    @abstractmethod
    def axes(self):
        pass

    @abstractmethod
    def validate(self, axes) -> bool:
        """returns true if the input axes can be resolved against the datacube axes"""

    @staticmethod
    def create(datacube, options, grid_options):
        if isinstance(datacube, (xr.core.dataarray.DataArray, xr.core.dataset.Dataset)):
            from .xarray import XArrayDatacube

            xadatacube = XArrayDatacube(datacube, options=options, grid_options=grid_options)
            return xadatacube
        else:
            return datacube
