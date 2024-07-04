import pandas as pd
import pytest
from helper_functions import find_nearest_latlon

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestHealpixNestedGrid:
    def setup_method(self, method):
        self.options = {
            "axis_config": [
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "healpix_nested",
                            "resolution": 128,
                            "axes": ["latitude", "longitude"],
                        }
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "d1", "expver": "0001", "levtype": "sfc", "stream": "clte"},
            "compressed_axes-config": [
                "longitude",
                "latitude",
            ],
        }

    @pytest.mark.internet
    def test_healpix_nested_grid(self):
        import pygribjump as gj

        request = Request(
            Select("activity", ["ScenarioMIP"]),
            Select("class", ["d1"]),
            Select("dataset", ["climate-dt"]),
            Select("date", [pd.Timestamp("20200102T010000")]),
            Select("experiment", ["SSP5-8.5"]),
            Select("expver", ["0001"]),
            Select("generation", ["1"]),
            Select("levtype", ["sfc"]),
            Select("model", ["IFS-NEMO"]),
            Select("param", ["167"]),
            Select("realization", ["1"]),
            Select("resolution", ["standard"]),
            Select("stream", ["clte"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [2, 2]),
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
        result.pprint()
        assert len(result.leaves) == 18

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            lon = cubepath["longitude"]
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("./tests/data/healpix_nested.grib", lat[0], lon[0])
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            assert eccodes_lat - tol <= lat[0]
            assert lat[0] <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon[0]
            assert lon[0] <= eccodes_lon + tol
        assert len(eccodes_lats) == 4
