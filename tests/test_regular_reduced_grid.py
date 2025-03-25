import pandas as pd
import pytest
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        # TODO: This uses the wrong fdb/schema/data so the hash for the grid is wrong
        # BUT the validation against eccodes is OK because the GRIB file is the same grid as Polytope returns
        self.options = {
            "axis_config": [
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
                            "type": "reduced_gaussian",
                            "resolution": 320,
                            "axes": ["latitude", "longitude"],
                            "md5_hash": "158db321ae8e773681eeb40e0a3d350f",
                        }
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
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "type": "fc", "stream": "oper"},
        }

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20231102T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [5, 5]),
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
        leaves = result.leaves
        assert len(leaves) == 18
        tot_leaves = 0
        for leaf in leaves:
            tot_leaves += len(leaf.result)
        assert tot_leaves == 324
        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-12
        f = open("tests/data/aifs_data_from_fdb.grib", "rb")
        messages = []
        message = codes_grib_new_from_file(f)
        messages.append(message)

        leaves = result.leaves
        for i in range(len(leaves)):
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lons_ = cubepath["longitude"]
            for lon in lons_:
                lats.append(lat)
                lons.append(lon)
                nearest_points = codes_grib_find_nearest(message, lat, lon)[0]
                eccodes_lat = nearest_points.lat
                eccodes_lon = nearest_points.lon
                eccodes_lats.append(eccodes_lat)
                eccodes_lons.append(eccodes_lon)
                assert eccodes_lat - tol <= lat
                assert lat <= eccodes_lat + tol
                assert eccodes_lon - tol <= lon
                assert lon <= eccodes_lon + tol
