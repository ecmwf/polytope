import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Point, Select


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        import pygribjump as gj

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
                        {
                            "name": "mapper",
                            "type": "local_regular",
                            "resolution": [80, 80],
                            "axes": ["latitude", "longitude"],
                            "local": [-40, 40, -20, 60],
                        }
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [-180, 180]}]},
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
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )

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
            Point(["latitude", "longitude"], [[-20, -20]]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == (-20,)
        assert result.leaves[0].flatten()["longitude"] == (-20,)

    @pytest.mark.fdb
    def test_fdb_datacube_2(self):
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
            Point(["latitude", "longitude"], [[-20, 50 + 360]]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["latitude"] == (-20,)
        assert result.leaves[0].flatten()["longitude"] == (50,)
