import pandas as pd
import pytest

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select, Span

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
            Select("step", ["2"]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20241015T000000")]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["d1"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Select("dataset", ["extremes-dt"]),
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
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
        assert len(result.leaves[0].result) == 3
        assert result.leaves[0].flatten()["longitude"][1] == 0.070093457944
        assert result.leaves[1].flatten()["longitude"][1] == 0.070148090413
        assert result.leaves[2].flatten()["longitude"][1] == 0.070202808112
        assert result.leaves[0].result[0] == 297.9250183105469
