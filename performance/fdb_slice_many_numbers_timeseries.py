import time

import pandas as pd
import pytest

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import All, Point, Select


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
            "number": {"transformation": {"type_change": "int"}},
            "longitude": {"transformation": {"cyclic": [0, 360]}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "type": "pf"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    # @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_fdb_datacube(self):
        request = Request(
            # Select("step", [0]),
            All("step"),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231205T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["enfo"]),
            Select("type", ["pf"]),
            # Select("latitude", [0.035149384216], method="surrounding"),
            # Select("latitude", [0.04], method="surrounding"),
            # Select("longitude", [0], method="surrounding"),
            Point(["latitude", "longitude"], [[0.04, 0]], method="surrounding"),
            All("number"),
        )
        time1 = time.time()
        result = self.API.retrieve(request)
        print(time.time() - time1)
        print(len(result.leaves))
        # result.pprint()
        # assert len(result.leaves) == 9
