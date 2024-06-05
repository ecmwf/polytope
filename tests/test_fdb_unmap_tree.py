import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select, Span

# import geopandas as gpd
# import matplotlib.pyplot as plt


class TestSlicingFDBDatacube:
    def setup_method(self, method):

        # Create a dataarray with 3 labelled axes using different index types
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

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
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
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            request=request,
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        self.API.datacube.prep_tree_encoding(result)
        result.pprint()
        for leaf in result.leaves:
            print(leaf.hidden)
