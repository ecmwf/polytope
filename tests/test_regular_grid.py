import pandas as pd
import pytest
from helper_functions import download_test_data, find_nearest_latlon

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Disk, Select

# import geopandas as gpd
# import matplotlib.pyplot as plt


class TestRegularGrid:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")
        self.options = {
            "values": {"mapper": {"type": "regular", "resolution": 30, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
            "latitude": {"reverse": {True}},
        }
        self.config = {"class": "ea", "expver": "0001", "levtype": "pl", "step": "0"}
        self.datacube_options = {"identical structure after": "number"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options, datacube_options=self.datacube_options)
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            axis_options=self.options,
            datacube_options=self.datacube_options,
        )

    @pytest.mark.fdb
    @pytest.mark.internet
    def test_regular_grid(self):
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
            Disk(["latitude", "longitude"], [0, 0], [3, 3]),
            Select("levelist", ["500"]),
            Select("number", ["0", "1"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 10

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        leaves = result.leaves
        for i in range(len(leaves)):
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"]
            lon = cubepath["longitude"]
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("./tests/data/era5-levels-members.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=16, c="red", cmap="YlOrRd")
        # plt.colorbar(label="Temperature")
        # plt.show()

        assert len(eccodes_lats) == 10
