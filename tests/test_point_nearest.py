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
            "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
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
            Select("date", [pd.Timestamp("20230625T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Point(["latitude", "longitude"], [[0.16, 0.176]], method="nearest"),
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1

    @pytest.mark.fdb
    def test_fdb_datacube_true_point(self):
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
            Point(["latitude", "longitude"], [[0.175746921078, 0.210608424337]], method="nearest"),
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 1

    @pytest.mark.fdb
    def test_fdb_datacube_true_point_2(self):
        request = Request(
            Select("step", [21, 22, 23]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[0.035149384216, 0.0]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 3

    @pytest.mark.fdb
    def test_fdb_datacube_true_point_3(self):
        request = Request(
            Select("step", [21]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[0.035149384216, -0.01]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].value == 359.929906542056
        assert result.leaves[0].axis.name == "longitude"

    @pytest.mark.fdb
    def test_fdb_datacube_true_point_5(self):
        request = Request(
            Select("step", [21]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[0.035149384216, 360 - 0.01]], method="nearest"),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].value == 359.929906542056
        assert result.leaves[0].axis.name == "longitude"

    @pytest.mark.fdb
    def test_fdb_datacube_true_point_4(self):
        request = Request(
            Select("step", [21]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[0.035149384216, 359.97]], method="nearest"),
        )
        result = self.API.retrieve(request)
        # result.pprint_2()
        assert len(result.leaves) == 1
        assert result.leaves[0].value == 359.929906542056
        assert result.leaves[0].axis.name == "longitude"
