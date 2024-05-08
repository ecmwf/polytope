import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Point, Select, Span


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "config": [
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ]
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "type": "fc", "stream": "oper"}
        self.fdbdatacube = FDBDatacube(
            self.config,
            axis_options=self.options,
            compressed_axes_options=[
                "longitude",
                "latitude",
                "levtype",
                "step",
                "date",
                "domain",
                "expver",
                "param",
                "class",
                "stream",
                "type",
            ],
        )
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            axis_options=self.options,
            compressed_axes_options=[
                "longitude",
                "latitude",
                "levtype",
                "step",
                "date",
                "domain",
                "expver",
                "param",
                "class",
                "stream",
                "type",
            ],
        )

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 9

    @pytest.mark.fdb
    def test_fdb_datacube_point(self):
        request = Request(
            Select("step", [0, 1]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240103T0000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[0.035149384216, 0.0]], method="surrounding"),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 6
        assert set(result.leaves[0].flatten()["step"]) == set((0, 1))

    @pytest.mark.fdb
    def test_fdb_datacube_point_v2(self):
        request = Request(
            Span("step", 0, 1),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240103T0000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Point(["latitude", "longitude"], [[0.035149384216, 0.0]], method="surrounding"),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 6
        assert len(result.leaves[0].result) == 2
