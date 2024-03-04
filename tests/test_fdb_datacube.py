import pandas as pd
import pytest

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select

# import geopandas as gpd
# import matplotlib.pyplot as plt


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "latitude": {"reverse": {True}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.fdbdatacube, engine=self.slicer, axis_options=self.options)

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230625T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 9

        # lats = []
        # lons = []
        # tol = 1e-8
        # for i in range(len(result.leaves)):
        #     cubepath = result.leaves[i].flatten()
        #     lat = cubepath["latitude"]
        #     lon = cubepath["longitude"]
        #     lats.append(lat)
        #     lons.append(lon)

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=16, c="red", cmap="YlOrRd")
        # plt.colorbar(label="Temperature")
        # plt.show()
