import pandas as pd
import pytest
from helper_functions import download_test_data

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Select


class TestRegularGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")
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
                        {"name": "mapper", "type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "ea", "expver": "0001", "levtype": "pl", "step": "0"},
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
                "levelist",
                "number",
            ],
        }

    @pytest.mark.internet
    @pytest.mark.fdb
    def test_incomplete_fdb_branch(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["pl"]),
            Select("date", [pd.Timestamp("20170102T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["129"]),
            Select("class", ["ea"]),
            Select("stream", ["enda"]),
            Select("type", ["an"]),
            Select("latitude", [0]),
            Select("longitude", [1]),
            Select("levelist", ["500"]),
            Select("number", ["0"]),
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
        assert len(result.leaves) == 1
        assert result.is_root()

    @pytest.mark.internet
    @pytest.mark.fdb
    def test_incomplete_fdb_branch_2(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["pl"]),
            Select("date", [pd.Timestamp("20170102T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["129"]),
            Select("class", ["ea"]),
            Select("stream", ["enda"]),
            Select("type", ["an"]),
            Select("latitude", [1]),
            Select("longitude", [0]),
            Select("levelist", ["500"]),
            Select("number", ["0"]),
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
        assert len(result.leaves) == 1
        assert result.is_root()
