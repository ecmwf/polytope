# import geopandas as gpd
# import matplotlib.pyplot as plt
import pandas as pd
import pytest
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file
from helper_functions import download_test_data

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestReducedLatLonGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/wave.grib"
        download_test_data(nexus_url, "wave.grib")
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
                        {"name": "mapper", "type": "reduced_ll", "resolution": 1441, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "od", "stream": "wave"},
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
                "direction",
                "frequency",
            ],
        }

    @pytest.mark.skip(reason="wave data grid packing not supported")
    @pytest.mark.internet
    @pytest.mark.fdb
    def test_reduced_ll_grid(self):
        import pygribjump as gj

        request = Request(
            Select("step", [1]),
            Select("date", [pd.Timestamp("20231129T000000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["140251"]),
            Select("direction", ["1"]),
            Select("frequency", ["1"]),
            Select("class", ["od"]),
            Select("stream", ["wave"]),
            Select("levtype", ["sfc"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [1.2, 1.5]),
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
        assert len(result.leaves) == 130

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        f = open("./tests/data/wave.grib", "rb")
        messages = []
        message = codes_grib_new_from_file(f)
        messages.append(message)

        leaves = result.leaves
        for i in range(len(leaves)):
            cubepath = leaves[i].flatten()
            tree_result = leaves[i].result[1]
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0]
            tree_result = leaves[i].result[1]
            del cubepath
            lats.append(lat)
            lons.append(lon)
            nearest_points = codes_grib_find_nearest(message, lat, lon)[0]
            eccodes_lat = nearest_points.lat
            eccodes_lon = nearest_points.lon
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)
            eccodes_resullt = nearest_points.value
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol
            assert tree_result == eccodes_resullt
        f.close()

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        # plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        # plt.colorbar(label="Temperature")
        # plt.show()
