import pandas as pd
import pytest

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select, Span, Union


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "axis_config": [
                {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
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
            ],
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
            "compressed_axes_config": [
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
        }

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Span("date", pd.Timestamp("20230625T120000"), pd.Timestamp("20230626T120000")),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Union(
                ["latitude", "longitude"],
                Point(["latitude", "longitude"], [[20, 20]], method="nearest"),
                Point(["latitude", "longitude"], [[0, 0]], method="nearest"),
                Point(["latitude", "longitude"], [[0, 20]], method="nearest"),
                Point(["latitude", "longitude"], [[25, 30]], method="nearest"),
                Point(["latitude", "longitude"], [[-30, 90]], method="nearest"),
                Point(["latitude", "longitude"], [[-60, -30]], method="nearest"),
                Point(["latitude", "longitude"], [[-15, -45]], method="nearest"),
                Point(["latitude", "longitude"], [[20, 0]], method="nearest"),
            ),
        )

        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 8

    @pytest.mark.fdb
    def test_fdb_datacube_surrounding(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Span("date", pd.Timestamp("20230625T120000"), pd.Timestamp("20230626T120000")),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Union(
                ["latitude", "longitude"],
                Point(["latitude", "longitude"], [[25, 30]], method="surrounding"),
                Point(["latitude", "longitude"], [[-15, -45]], method="surrounding"),
            ),
        )

        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 4
        tot_leaves = 0
        for leaf in result.leaves:
            tot_leaves += len(leaf.result)
        assert tot_leaves == 9

    @pytest.mark.fdb
    def test_fdb_datacube_axis_order(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Span("date", pd.Timestamp("20230625T120000"), pd.Timestamp("20230626T120000")),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Union(
                ["latitude", "longitude"],
                Point(["latitude", "longitude"], [[25, 30]], method="nearest"),
            ),
        )

        inverted_request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Span("date", pd.Timestamp("20230625T120000"), pd.Timestamp("20230626T120000")),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Union(
                ["longitude", "latitude"],
                Point(["longitude", "latitude"], [[30, 25]], method="nearest"),
            ),
        )

        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        inverted_result = self.API.retrieve(inverted_request)
        result.pprint()
        inverted_result.pprint()
        assert len(result.leaves) == 1
        assert len(inverted_result.leaves) == 1
        assert inverted_result.leaves[0].result == result.leaves[0].result

    # @pytest.mark.fdb
    # def test_fdb_datacube_mix_methods(self):
    #     import pygribjump as gj

    #     request = Request(
    #         Select("step", [0]),
    #         Select("levtype", ["sfc"]),
    #         Span("date", pd.Timestamp("20230625T120000"), pd.Timestamp("20230626T120000")),
    #         Select("domain", ["g"]),
    #         Select("expver", ["0001"]),
    #         Select("param", ["167"]),
    #         Select("class", ["od"]),
    #         Select("stream", ["oper"]),
    #         Select("type", ["an"]),
    #         Union(["latitude", "longitude"],
    #               Point(["latitude", "longitude"], [[25, 30]], method="nearest"),
    #               Point(["latitude", "longitude"], [[-15, -45]], method="surrounding"))
    #     )

    #     self.fdbdatacube = gj.GribJump()
    #     self.slicer = HullSlicer()
    #     self.API = Polytope(
    #         datacube=self.fdbdatacube,
    #         engine=self.slicer,
    #         options=self.options,
    #     )
    #     result = self.API.retrieve(request)
    #     result.pprint()
    #     assert len(result.leaves) == 6
