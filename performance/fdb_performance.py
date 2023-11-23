import time

import pandas as pd

from polytope.datacube.backends.fdb import FDBDatacube
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
            "date": {"transformation": {"merge": {"with": "time", "linkers": [" ", "00"]}}},
            "step": {"transformation": {"type_change": "int"}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "step": 0}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    # @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230625T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Box(["latitude", "longitude"], [0, 0], [10, 10]),
        )
        time1 = time.time()
        result = self.API.retrieve(request)
        print("ENTIRE TIME")
        print(time.time() - time1)
        print("TIME IN GET 2nd LAST VAL")
        print(self.fdbdatacube.second_val_time)
        print("TIME GET LAST LAYER BEFORE LEAF")
        print(self.fdbdatacube.first_val_time)
        print("TIME GIVE FDB VAL TO NODE")
        print(self.fdbdatacube.time_give_fdb_val_to_node)
        print("TIME FIND FDB VALUES")
        print(self.fdbdatacube.time_find_fdb_values)
        print("TIME FDB EXTRACT ONLY")
        print(self.fdbdatacube.time_fdb_extract)
        print(len(result.leaves))
