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
            Point(["latitude", "longitude"], [[0.16, 0.176]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == 0
        assert result.leaves[0].flatten()["longitude"] == 0

    @pytest.mark.fdb
    def test_point_outside_local_region(self):
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
            Point(["latitude", "longitude"], [[0.16, 61]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == 0
        assert result.leaves[0].flatten()["longitude"] == 60

    @pytest.mark.fdb
    def test_point_outside_local_region_2(self):
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
            Point(["latitude", "longitude"], [[41, 1]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == 40
        assert result.leaves[0].flatten()["longitude"] == 1

    @pytest.mark.fdb
    def test_point_outside_local_region_3(self):
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
            Point(["latitude", "longitude"], [[1, 61]]),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.is_root()

    @pytest.mark.fdb
    def test_point_outside_local_region_4(self):
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
            Point(["latitude", "longitude"], [[41, 1]]),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.is_root()

    @pytest.mark.fdb
    def test_point_outside_local_region_5(self):
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
            Point(["latitude", "longitude"], [[-41, 1]]),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.is_root()

    @pytest.mark.fdb
    def test_point_outside_local_region_6(self):
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
            Point(["latitude", "longitude"], [[-30, -21]]),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.is_root()

    @pytest.mark.fdb
    def test_point_outside_local_region_7(self):
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
            Point(["latitude", "longitude"], [[-41, 1]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == -40
        assert result.leaves[0].flatten()["longitude"] == 1

    @pytest.mark.fdb
    def test_point_outside_local_region_8(self):
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
            Point(["latitude", "longitude"], [[-30, -21]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == -30
        assert result.leaves[0].flatten()["longitude"] == -20

    @pytest.mark.fdb
    def test_point_outside_local_region_9(self):
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
            Point(["latitude", "longitude"], [[-30, -21]], method="surrounding"),
        )
        result = self.API.retrieve(request)
        result.pprint_2()
        assert len(result.leaves) == 3
        assert result.leaves[0].flatten()["latitude"] == -31
        assert result.leaves[0].flatten()["longitude"] == -20
