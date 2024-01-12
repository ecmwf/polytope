import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select, Span


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "values": {"mapper": {"type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["pl"]),
            Span("date", pd.Timestamp("20170101T120000"), pd.Timestamp("20170102T120000")),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["129"]),
            Select("class", ["ea"]),
            Select("stream", ["enda"]),
            Select("type", ["an"]),
            Select("latitude", [0]),
            Select("longitude", [0]),
            Select("levelist", ["500", "850"]),
            Select("number", ["0"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 6
