import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import All, Select, Span


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
            "axis_config": [{"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]}],
            "compressed_axes_config": ["date", "step", "level", "longitude"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=array,
            engine=self.slicer,
            options=self.options,
        )

    def test_all(self):
        request = Request(Select("step", [3]), Select("date", ["2000-01-01"]), All("level"), Select("longitude", [1]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["level"] == tuple(range(1, 130))

    def test_all_cyclic(self):
        request = Request(Select("step", [3]), Select("date", ["2000-01-01"]), Select("level", [1]), All("longitude"))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["longitude"] == tuple(range(0, 360))

    @pytest.mark.fdb
    def test_all_mapper_cyclic(self):
        import pygribjump as gj

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
                        {
                            "name": "mapper",
                            "type": "octahedral",
                            "resolution": 1280,
                            "axes": ["latitude", "longitude"],
                            "md5_hash": "5ea6378bf5e2904f565ef7221da63a09",
                        }
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
        }
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()

        request = Request(
            Select("step", [11]),
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
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, options=self.options)
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert len(result.leaves[0].result) == 20
        assert result.leaves[0].values == (
            0.0,
            18.0,
            36.0,
            54.0,
            72.0,
            90.0,
            108.0,
            126.0,
            144.0,
            162.0,
            180.0,
            198.0,
            216.0,
            234.0,
            252.0,
            270.0,
            288.0,
            306.0,
            324.0,
            342.0,
        )
