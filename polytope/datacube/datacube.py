import xarray as xr
from abc import ABC, abstractmethod
from typing import Any, List

from .datacube_request_tree import DatacubeRequestTree, DatacubePath
from .datacube_axis import DatacubeAxis


class Datacube(ABC):

    @abstractmethod
    def get(self, requests: List[DatacubeRequestTree]) -> Any:
        """Return data given a set of request trees"""

    @abstractmethod
    def get_mapper(self, label) -> DatacubeAxis:
        """
        Get the type mapper for a subaxis of the datacube given by label
        """
    
    @abstractmethod
    def get_indices(self, path: DatacubePath, label: str, lower: Any, upper: Any) -> List:
        """
        Given a path to a subset of the datacube, return the discrete indexes which exist between
        two non-discrete values (lower, upper) for a particular axis (given by label)
        If lower and upper are equal, returns the index which exactly matches that value (if it exists)
        e.g. returns integer discrete points between two floats
        """

    @property
    @abstractmethod
    def axes(self):
        pass

    @abstractmethod
    def validate(self, axes) -> bool:
        """ returns true if the input axes can be resolved against the datacube axes """


    @staticmethod
    def create(datacube, options):
        if isinstance(datacube, (xr.core.dataarray.DataArray, xr.core.dataset.Dataset)):
            from .xarray import XArrayDatacube
            xadatacube = XArrayDatacube(datacube, options = options)
            return xadatacube

