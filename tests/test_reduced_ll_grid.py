# import geopandas as gpd
# import matplotlib.pyplot as plt
import pandas as pd
import pytest
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file
from helper_functions import download_test_data

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestReducedLatLonGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/wave.grib"
        download_test_data(nexus_url, "wave.grib")
        self.options = {
            "values": {
                "transformation": {
                    "mapper": {"type": "reduced_ll", "resolution": 1441, "axes": ["latitude", "longitude"]}
                }
            },
            "date": {"transformation": {"merge": {"with": "time", "linkers": ["T", "00"]}}},
            "step": {"transformation": {"type_change": "int"}},
            "number": {"transformation": {"type_change": "int"}},
            "longitude": {"transformation": {"cyclic": [0, 360]}},
        }
        self.config = {"class": "od", "stream": "wave"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    @pytest.mark.internet
    @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_reduced_ll_grid(self):
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
            lat = cubepath["latitude"]
            lon = cubepath["longitude"]
            del cubepath
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
        f.close()

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        # plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        # plt.colorbar(label="Temperature")
        # plt.show()
