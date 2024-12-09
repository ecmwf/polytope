import pandas as pd
import pytest

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select, Span, Union


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

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])

        box2 = Box(["latitude", "longitude"], [0.1, 0.1], [0.3, 0.3])

        union = Union(["latitude", "longitude"], box1, box2)

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
            union,
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
        assert len(result.leaves) == 6
        total_lons = 0
        total_vals = 0
        for leaf in result.leaves:
            total_lons += len(leaf.values)
            total_vals += len(leaf.result)
        assert total_lons == 16
        assert total_vals == 16

    @pytest.mark.fdb
    def test_fdb_datacube_complete_overlap(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])

        box2 = Box(["latitude", "longitude"], [0, 0], [0.1, 0.1])

        union = Union(["latitude", "longitude"], box1, box2)

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
            union,
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
        total_lons = 0
        total_vals = 0
        for leaf in result.leaves:
            total_lons += len(leaf.values)
            total_vals += len(leaf.result)
        assert total_lons == 9
        assert total_vals == 9

    @pytest.mark.fdb
    def test_fdb_datacube_complete_overlap_v2(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])

        box2 = Box(["latitude", "longitude"], [0.1, 0.05], [0.2, 0.2])

        union = Union(["latitude", "longitude"], box2, box1)

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
            union,
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
        assert len(result.leaves) == 3
        total_lons = 0
        total_vals = 0
        for leaf in result.leaves:
            total_lons += len(leaf.values)
            total_vals += len(leaf.result)
        assert total_lons == 9
