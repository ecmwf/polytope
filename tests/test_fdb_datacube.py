import pandas as pd
import pytest

from polytope.datacube.backends.FDB_datacube import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "values": {
                "transformation": {
                    "mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                }
            },
            "date": {"transformation": {"merge": {"with": "time", "linkers": ["T", "00"]}}},
            "step": {"transformation": {"type_change": "int"}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "step": 11}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [11]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230710T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["151130"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 9
