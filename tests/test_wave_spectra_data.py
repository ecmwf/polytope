import pandas as pd
import pytest
from helper_functions import find_nearest_latlon

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestWaveData:
    def setup_method(self, method):
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
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
            ],
            "pre_path": {"class": "od", "expver": "0001", "type": "fc", "stream": "wave", "date": "20250201"},
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
        self.slicer = HullSlicer()

    @pytest.mark.fdb
    def test_healpix_grid(self):
        import pygribjump as gj

        self.fdb_datacube = gj.GribJump()
        self.API = Polytope(
            datacube=self.fdb_datacube,
            engine=self.slicer,
            options=self.options,
        )

        request = Request(
            Select("step", [1]),
            Select("date", [pd.Timestamp("20250201T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["140251"]),
            Select("class", ["od"]),
            Select("stream", ["wave"]),
            Select("type", ["fc"]),
            Select("direction", ["1"]),
            Select("frequency", ["1"]),
            Box(["latitude", "longitude"], [1, 1], [2, 2]),
            Select("levtype", ["sfc"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 14
        assert result.leaves[0].result[1].size == 1
        assert result.leaves[1].result[1].size == 1

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        leaves = result.leaves
        for i, leaf in enumerate(leaves):
            cubepath = leaf.flatten()
            lat = cubepath["latitude"][0]
            new_lons = cubepath["longitude"]
            for j, lon in enumerate(new_lons):
                lats.append(lat)
                lons.append(lon)
                nearest_points = find_nearest_latlon("./tests/data/wave_spectra.grib", lat, lon)
                eccodes_lat = nearest_points[0][0]["lat"]
                eccodes_lon = nearest_points[0][0]["lon"]
                assert eccodes_lat - tol <= lat
                assert lat <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon
                assert lon <= eccodes_lon + tol
                tol = 1e-2
            eccodes_lats.append(lat)
        assert len(eccodes_lats) == 14
