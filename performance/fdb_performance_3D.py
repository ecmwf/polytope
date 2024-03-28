import time

import pandas as pd

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select, Span


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "values": {
                    "mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
            },
            "date": {"merge": {"with": "time", "linkers": [" ", "00"]}},
            "step": {"type_change": "int"},
            "levelist": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    # @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_fdb_datacube(self):
        request = Request(
            Span("step", 1, 15),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [3, 5]),
        )
        time1 = time.time()
        result = self.API.retrieve(request)
        print("ENTIRE TIME")
        print(time.time() - time1)
        print(len(result.leaves))
