import numpy as np
import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select, Span


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        import pygribjump as gj

        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "config": [
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {"axis_name": "levelist", "transformations": [{"name": "type_change", "type": "int"}]},
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ]
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl", "stream": "enda"}
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            config=self.config,
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
                "number",
                "levelist",
            ],
        )

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["pl"]),
            Span("date", pd.Timestamp("20170101T120000"), pd.Timestamp("20170102T120000")),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["129"]),
            Select("class", ["ea"]),
            Select("stream", ["enda"]),
            Select("type", ["an"]),
            Select("latitude", [0]),
            Select("longitude", [0]),
            Select("levelist", ["500", "850"]),
            Select("number", ["0"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 3
        path1 = result.leaves[0].flatten()
        assert path1["date"] == (np.datetime64("2017-01-01T12:00:00"),)
        assert set(path1["levelist"]) == set((850, 500))
        assert len(result.leaves[0].result) == 2
