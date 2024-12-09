import time

import pandas as pd
import pytest

from polytope_feature.datacube.tree_encoding import decode_tree, encode_tree
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import All, Box, Select


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
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "type": "pf"},
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
                "number",
            ],
        }

    # Testing different shapes
    @pytest.mark.skip(reason="optimisation test")
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        import pygribjump as gj

        request = Request(
            All("step"),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231205T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["enfo"]),
            Select("type", ["pf"]),
            Box(["latitude", "longitude"], [-20, 61], [48, 36]),
            All("number"),
        )

        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        time1 = time.time()
        result = self.API.retrieve(request)
        time2 = time.time()
        self.fdb_datacube = self.API.datacube
        self.fdb_datacube.prep_tree_encoding(result)
        result.pprint()
        print("PREP TREE ENCODING MAPPINGS")
        print(time.time() - time2)
        time3 = time.time()
        encoded_bytes = encode_tree(result)
        print("TREE ENCODING")
        print(time.time() - time3)
        time4 = time.time()
        decoded_tree = decode_tree(self.fdb_datacube, encoded_bytes)
        print("TREE DECODING")
        print(time.time() - time4)
        decoded_tree.pprint()
        print(time.time() - time1)
        print(len(result.leaves[0].result))
        for leaf in result.leaves:
            assert leaf.result is not None
        assert len(result.leaves) == 968
