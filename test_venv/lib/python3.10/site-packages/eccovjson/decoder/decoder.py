import json
from abc import ABC, abstractmethod

from eccovjson.Coverage import Coverage
from eccovjson.CoverageCollection import CoverageCollection


class Decoder(ABC):
    def __init__(self, covjson):
        # if python dictionary no need for loading, otherwise load json file
        if isinstance(covjson, dict):
            self.covjson = covjson
        elif isinstance(covjson, str):
            with open(covjson) as json_file:
                self.covjson = json.load(json_file)
        else:
            raise TypeError("Covjson must be dictionary or covjson file")

        self.type = self.get_type()

        if self.type == "Coverage":
            self.coverage = Coverage(self.covjson)
        elif self.type == "CoverageCollection":
            self.coverage = CoverageCollection(self.covjson)
        else:
            raise TypeError("Type must be Coverage or CoverageCollection")

        self.parameters = self.get_parameters()
        self.coordinates = self.get_referencing()
        self.mars_metadata = self.get_mars_metadata()

    def get_type(self):
        return self.covjson["type"]

    def get_parameters(self):
        return list(self.covjson["parameters"].keys())

    def get_parameter_metadata(self, parameter):
        return self.covjson["parameters"][parameter]

    def get_referencing(self):
        coordinates = []
        for coords in self.covjson["referencing"]:
            coordinates.append(coords["coordinates"])
        return [coord for sublist in coordinates for coord in sublist]

    def get_mars_metadata(self):
        mars_metadata = []
        for coverage in self.coverage.coverages:
            mars_metadata.append(coverage["mars:metadata"])
        return mars_metadata

    @abstractmethod
    def get_ranges(self):
        pass

    @abstractmethod
    def get_domains(self):
        pass

    @abstractmethod
    def get_coordinates(self):
        pass

    @abstractmethod
    def get_values(self):
        pass

    @abstractmethod
    def to_geopandas(self):
        pass

    @abstractmethod
    def to_xarray(self):
        pass
