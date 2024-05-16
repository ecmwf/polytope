import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import All, Select, Span


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129, 360),
            dims=("date", "step", "level", "longitude"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "longitude": range(0, 360),
            },
        )
        self.options = {
            "config": [{"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]}]
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=self.options)

    def test_all(self):
        request = Request(Select("step", [3]), Select("date", ["2000-01-01"]), All("level"), Select("longitude", [1]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 129

    def test_all_cyclic(self):
        request = Request(Select("step", [3]), Select("date", ["2000-01-01"]), Select("level", [1]), All("longitude"))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 360

    @pytest.mark.fdb
    def test_all_mapper_cyclic(self):
        from polytope.datacube.backends.fdb import FDBDatacube

        self.options = {
            "config": [
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
            ]
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "step": "11"}
        # self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        # self.slicer = HullSlicer()
        # self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

        request = Request(
            Select("step", [11]),
            Select("number", [1]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230710T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["151130"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Span("latitude", 89.9, 90),
            All("longitude"),
        )
        self.fdbdatacube = FDBDatacube(request, self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)
        result = self.API.retrieve(request)
        # result.pprint()
        assert len(result.leaves) == 20
