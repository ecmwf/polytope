import pandas as pd
import pytest
from helper_functions import download_test_data

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select


class TestRegularGrid:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")
        self.options = {
            "values": {"mapper": {"type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": [" ", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl", "step": "0"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    @pytest.mark.internet
    @pytest.mark.fdb
    def test_incomplete_fdb_branch(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["pl"]),
            Select("date", [pd.Timestamp("20170102T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["129"]),
            Select("class", ["ea"]),
            Select("stream", ["enda"]),
            Select("type", ["an"]),
            Select("latitude", [0]),
            Select("longitude", [1]),
            Select("levelist", ["500"]),
            Select("number", ["0"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.is_root()

    @pytest.mark.internet
    @pytest.mark.fdb
    def test_incomplete_fdb_branch_2(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["pl"]),
            Select("date", [pd.Timestamp("20170102T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["129"]),
            Select("class", ["ea"]),
            Select("stream", ["enda"]),
            Select("type", ["an"]),
            Select("latitude", [1]),
            Select("longitude", [0]),
            Select("levelist", ["500"]),
            Select("number", ["0"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.is_root()
