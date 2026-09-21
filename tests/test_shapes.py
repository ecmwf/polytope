import numpy as np
import pandas as pd
import pytest
import xarray as xr

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
            "axis_config": [
                {
                    "axis_name": "longitude",
                    "transformations": [{"name": "cyclic", "range": [0, 360]}],
                }
            ],
            "compressed_axes_config": ["date", "step", "level", "longitude"],
        }
        self.API = Polytope(
            datacube=array,
            options=self.options,
        )

    def test_all(self):
        request = Request(
            Select("step", [3]),
            Select("date", ["2000-01-01"]),
            All("level"),
            Select("longitude", [1]),
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["level"] == tuple(range(1, 130))

    def test_all_cyclic(self):
        request = Request(
            Select("step", [3]),
            Select("date", ["2000-01-01"]),
            Select("level", [1]),
            All("longitude"),
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["longitude"] == tuple(range(0, 360))

    @pytest.mark.fdb
    def test_all_mapper_cyclic(self):
        import pygribjump as gj

        self.options = {
            "axis_config": [
                {
                    "axis_name": "number",
                    "transformations": [{"name": "type_change", "type": "int"}],
                },
                {
                    "axis_name": "step",
                    "transformations": [{"name": "type_change", "type": "int"}],
                },
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
                        }
                    ],
                },
                {
                    "axis_name": "latitude",
                    "transformations": [{"name": "reverse", "is_reverse": True}],
                },
                {
                    "axis_name": "longitude",
                    "transformations": [{"name": "cyclic", "range": [0, 360]}],
                },
            ],
            "pre_path": {
                "class": "od",
                "expver": "0001",
                "levtype": "sfc",
                "type": "fc",
                "stream": "oper",
            },
        }
        self.fdbdatacube = gj.GribJump()

        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240103T0000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Span("latitude", 89.9, 90),
            All("longitude"),
        )
        self.API = Polytope(datacube=self.fdbdatacube, options=self.options)
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

    def test_close_points(self):
        from types import MethodType

        from polytope_feature.datacube.backends.mock import MockDatacube
        from polytope_feature.polytope import Polytope, Request
        from polytope_feature.shapes import Point

        GRID = {"latitude": [50.70, 50.725, 50.74166666666788, 50.76, 60.0], "longitude": [7.0, 7.108, 7.2]}

        cube = MockDatacube({"latitude": 100, "longitude": 100}, ["longitude"])
        cube.get_indices = MethodType(
            lambda self, path, axis, lower, upper, method=None: axis.find_standard_indices_between(
                GRID[axis.name], lower, upper, self, method
            ),
            cube,
        )
        points = [[50.725, 7.108], [50.7417, 7.1083]]
        result = Polytope(cube).retrieve(Request(Point(["latitude", "longitude"], points, method="nearest")))
        assert len(result.leaves) == 3
        for leaf in result.leaves:
            assert len(leaf.values) == 3
