import pandas as pd
import pytest
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file
from helper_functions import download_test_data

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Point, Select

# import geopandas as gpd
# import matplotlib.pyplot as plt


class TestRegularGrid:
    def setup_method(self, method):
        from polytope.datacube.backends.fdb import FDBDatacube

        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")
        self.options = {
            "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
            "longitude": {"cyclic": [0, 360]},
            "latitude": {"reverse": {True}},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper", "type": "fc"}
        self.datacube_options = {"identical structure after": "number"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options, datacube_options=self.datacube_options)
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            axis_options=self.options,
            datacube_options=self.datacube_options,
        )

    def find_nearest_latlon(self, grib_file, target_lat, target_lon):
        # Open the GRIB file
        f = open(grib_file)

        # Load the GRIB messages from the file
        messages = []
        while True:
            message = codes_grib_new_from_file(f)
            if message is None:
                break
            messages.append(message)

        # Find the nearest grid points
        nearest_points = []
        for message in messages:
            nearest_index = codes_grib_find_nearest(message, target_lat, target_lon)
            nearest_points.append(nearest_index)

        # Close the GRIB file
        f.close()

        return nearest_points

    @pytest.mark.fdb
    @pytest.mark.internet
    def test_regular_grid(self):
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
            Point(["latitude", "longitude"], [[39, 360 - 76.45]], method="nearest"),
        )
        result = self.API.retrieve(request)
        longitude_val_1 = result.leaves[0].flatten()["longitude"]
        result.pprint_2()
        assert longitude_val_1 == 283.561643835616

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
            Point(["latitude", "longitude"], [[39, -76.45]], method="nearest"),
        )
        result = self.API.retrieve(request)
        longitude_val_1 = result.leaves[0].flatten()["longitude"]
        result.pprint_2()
        assert longitude_val_1 == 283.561643835616
