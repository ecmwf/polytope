import pandas as pd
import pytest

from polytope.datacube.tree_encoding import decode_tree, encode_tree
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestEncoder:
    def setup_method(self):
        from polytope.datacube.backends.fdb import FDBDatacube

        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "latitude": {"reverse": {True}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper", "type": "fc"}
        self.datacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.datacube, engine=self.slicer, axis_options=self.options)
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240118T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["49", "167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [5, 5]),
        )
        self.tree = self.API.retrieve(request)

    @pytest.mark.fdb
    def test_encoding(self):
        import time

        time0 = time.time()
        encode_tree(self.tree)
        time1 = time.time()
        print("TIME TO ENCODE")
        print(time1 - time0)
        print(len(self.tree.leaves))
        time2 = time.time()
        decoded_tree = decode_tree(self.datacube)
        time3 = time.time()
        print("TIME TO DECODE")
        print(time3 - time2)
        decoded_tree.pprint()
