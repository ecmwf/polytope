import numpy as np
import pandas as pd
import pytest

from polytope.datacube.backends.mock import MockDatacube
from polytope.datacube.backends.fdb import FDBDatacube
from polytope.datacube.datacube_axis import (
    FloatDatacubeAxis,
    IntDatacubeAxis,
    PandasTimedeltaDatacubeAxis,
    PandasTimestampDatacubeAxis,
    UnsliceableDatacubeAxis,
)
from polytope.datacube.tensor_index_tree import TensorIndexTree
from polytope.datacube.tree_encoding import decode_tree, encode_tree, write_encoded_tree_to_file


class TestEncoder:
    def setup_method(self):
        pass

    @pytest.mark.fdb
    def test_encoding(self):
        from polytope.engine.hullslicer import HullSlicer
        from polytope.polytope import Polytope, Request
        from polytope.shapes import Box, Select
        import pygribjump as gj
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
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
        )
        self.options = {
            "axis_config": [
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
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
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
        }
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            request=request,
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        result.pprint()
        fdb_datacube = self.API.datacube
        fdb_datacube.prep_tree_encoding(result)
        encoded_bytes = encode_tree(result)
        # write_encoded_tree_to_file(encoded_bytes)
        decoded_tree = decode_tree(fdb_datacube, encoded_bytes)
        decoded_tree.pprint()
        assert decoded_tree.leaves[0].result_size == [1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
        assert decoded_tree.leaves[0].indexes_size == [3, 3, 3]
