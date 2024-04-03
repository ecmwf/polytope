import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Point, Select


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "values": {
                "mapper": {
                    "type": "local_regular",
                    "resolution": [80, 80],
                    "axes": ["latitude", "longitude"],
                    "local": [-40, 40, -20, 60],
                }
            },
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [-180, 180]},
            "latitude": {"reverse": {True}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240129T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[-20, -20]]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == (-20,)
        assert result.leaves[0].flatten()["longitude"] == (-20,)

    @pytest.mark.fdb
    def test_fdb_datacube_2(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240129T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[-20, 50 + 360]]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == (-20,)
        assert result.leaves[0].flatten()["longitude"] == (50,)
