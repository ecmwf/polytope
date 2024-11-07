from abc import ABC, abstractmethod

from eccovjson.Coverage import Coverage
from eccovjson.CoverageCollection import CoverageCollection


class Encoder(ABC):
    def __init__(self, type, domaintype):
        self.covjson = {}

        self.type = type
        self.parameters = []
        self.covjson["type"] = self.type
        self.covjson["domainType"] = domaintype
        self.covjson["coverages"] = []
        self.covjson["parameters"] = {}
        self.covjson["referencing"] = []

        if type == "Coverage":
            self.coverage = Coverage(self.covjson)
        elif type == "CoverageCollection":
            self.coverage = CoverageCollection(self.covjson)
        else:
            raise TypeError("Type must be Coverage or CoverageCollection")

    def add_parameter(self, param):
        param = self.convert_param_id_to_param(param)
        if param == "t" or param == "167":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "Temperature",
                "unit": {"symbol": "K"},
                "observedProperty": {
                    "id": "t",
                    "label": {"en": "Temperature"},
                },
            }
        elif param == "tp" or param == "228":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "Total Precipitation",
                "unit": {"symbol": "m"},
                "observedProperty": {
                    "id": "tp",
                    "label": {"en": "Total Precipitation"},
                },
            }
        elif param == "10u" or param == "165":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "10 metre U wind component",
                "unit": {"symbol": "ms-1"},
                "observedProperty": {
                    "id": "10u",
                    "label": {"en": "10 metre U wind component"},
                },
            }
        elif param == "10v" or param == "166":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "10 metre V wind component",
                "unit": {"symbol": "ms-1"},
                "observedProperty": {
                    "id": "10v",
                    "label": {"en": "10 metre V wind component"},
                },
            }
        elif param == "10fg" or param == "49":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "Maximum 10 metre wind gust since previous post-processing",
                "unit": {"symbol": "ms-1"},
                "observedProperty": {
                    "id": "10fg",
                    "label": {"en": "Maximum 10 metre wind gust since previous post-processing"},
                },
            }
        elif param == "tcc" or param == "164":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "Total cloud cover",
                "unit": {"symbol": ""},
                "observedProperty": {
                    "id": "tcc",
                    "label": {"en": "Total cloud cover"},
                },
            }
        elif param == "2d" or param == "168":
            self.covjson["parameters"][param] = {
                "type": "Parameter",
                "description": "2 metre dewpoint temperature",
                "unit": {"symbol": "K"},
                "observedProperty": {
                    "id": "2d",
                    "label": {"en": "2 metre dewpoint temperature"},
                },
            }
        self.parameters.append(param)

    def add_reference(self, reference):
        self.covjson["referencing"].append(reference)

    def convert_param_id_to_param(self, paramid):
        try:
            param = int(paramid)
        except BaseException:
            return paramid
        if param == 165:
            return "10u"
        elif param == 166:
            return "10v"
        elif param == 167:
            return "t"
        elif param == 228:
            return "tp"
        elif param == 49:
            return "10fg"
        elif param == 164:
            return "tcc"
        elif param == 168:
            return "2d"

    @abstractmethod
    def add_coverage(self, mars_metadata, coords, values):
        pass

    @abstractmethod
    def add_domain(self, coverage, domain):
        pass

    @abstractmethod
    def add_range(self, coverage, range):
        pass

    @abstractmethod
    def add_mars_metadata(self, coverage, metadata):
        pass

    @abstractmethod
    def from_xarray(self, dataset):
        pass

    @abstractmethod
    def from_polytope(self, result):
        pass
