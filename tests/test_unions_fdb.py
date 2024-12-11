import pandas as pd
import pytest

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Disk, Select, Span, Union


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
    def test_fdb_datacube_box_union(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Box(["latitude", "longitude"], [0.3, 0], [0.4, 0.2])

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
            Union(["latitude", "longitude"], box1, box2),
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
        leaves = result.leaves
        assert len(leaves) == 5
        total_leaves = 0
        for i in range(len(leaves)):
            total_leaves += len(leaves[i].values)
        assert total_leaves == 15

    @pytest.mark.fdb
    def test_fdb_datacube_union_disk(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Disk(["latitude", "longitude"], [0.5, 0], [0.1, 0.1])

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
            Union(["latitude", "longitude"], box1, box2),
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
        leaves = result.leaves
        # assert len(leaves) == 16
        total_leaves = 0
        for i in range(len(leaves)):
            total_leaves += len(leaves[i].values)
        assert total_leaves == 16

    @pytest.mark.fdb
    def test_fdb_datacube_disk_union_intersecting(self):
        import pygribjump as gj

        box1 = Disk(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Disk(["latitude", "longitude"], [0.1, 0], [0.2, 0.2])

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
            Union(["latitude", "longitude"], box1, box2),
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
        leaves = result.leaves
        # assert len(leaves) == 31
        total_leaves = 0
        for i in range(len(leaves)):
            total_leaves += len(leaves[i].values)
        assert total_leaves == 31

    @pytest.mark.fdb
    def test_fdb_datacube_box_union_total_overlap(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])

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
            Union(["latitude", "longitude"], box1, box2),
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
        leaves = result.leaves
        # assert len(leaves) == 3
        total_leaves = 0
        for i in range(len(leaves)):
            total_leaves += len(leaves[i].values)
        assert total_leaves == 9

    @pytest.mark.fdb
    def test_fdb_datacube_box_union_disk_overlap(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Disk(["latitude", "longitude"], [0.3, 0], [0.2, 0.2])

        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )

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
            Union(["latitude", "longitude"], box1, box2),
        )

        result = self.API.retrieve(request)
        result.pprint()
        leaves = result.leaves
        # assert len(leaves) == 29
        total_leaves_1 = 0
        for i in range(len(leaves)):
            total_leaves_1 += len(leaves[i].values)
        assert total_leaves_1 == 29

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
            Union(["latitude", "longitude"], box2, box1),
        )

        result = self.API.retrieve(request)
        result.pprint()
        leaves = result.leaves
        # assert len(leaves) == 29
        total_leaves_2 = 0
        for i in range(len(leaves)):
            total_leaves_2 += len(leaves[i].values)
        assert total_leaves_2 == total_leaves_1

    @pytest.mark.fdb
    def test_fdb_datacube_box_union_intersecting(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Box(["latitude", "longitude"], [0.1, 0], [0.3, 0.2])

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
            Union(["latitude", "longitude"], box1, box2),
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
        leaves = result.leaves
        # assert len(leaves) == 4
        total_leaves = 0
        for i in range(len(leaves)):
            total_leaves += len(leaves[i].values)
        assert total_leaves == 12

    @pytest.mark.fdb
    def test_fdb_datacube_union_disk_intersecting(self):
        import pygribjump as gj

        box1 = Box(["latitude", "longitude"], [0, 0], [0.2, 0.2])
        box2 = Disk(["latitude", "longitude"], [0.2, 0], [0.1, 0.1])

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
            Union(["latitude", "longitude"], box1, box2),
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
        leaves = result.leaves
        # assert len(leaves) == 13
        total_leaves = 0
        for i in range(len(leaves)):
            total_leaves += len(leaves[i].values)
        assert total_leaves == 13
