import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd
import pytest
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Ellipsoid, Path, Select
from tests.helper_functions import download_test_data


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

    def find_nearest_latlon(self, grib_file, target_lat, target_lon):
        messages = grib_file

        # Find the nearest grid points
        nearest_points = []
        for message in [messages[0]]:
            nearest_index = codes_grib_find_nearest(message, target_lat, target_lon)
            nearest_points.append(nearest_index)

        return nearest_points

    @pytest.mark.internet
    @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_reduced_ll_grid(self):
        shapefile = gpd.read_file("./examples/data/Shipping-Lanes-v1.shp")
        geometry_multiline = shapefile.iloc[2]
        geometry_object = geometry_multiline["geometry"]

        lines = []
        i = 0

        for line in geometry_object[:7]:
            for point in line.coords:
                point_list = list(point)
                if list(point)[0] < 0:
                    point_list[0] = list(point)[0] + 360
                lines.append(point_list)

        # Append for each point a corresponding step

        new_points = []
        for point in lines[:7]:
            new_points.append([point[1], point[0], 1])

        # Pad the shipping route with an initial shape

        padded_point_upper = [0.24, 0.24, 1]
        padded_point_lower = [-0.24, -0.24, 1]
        initial_shape = Ellipsoid(["latitude", "longitude", "step"], padded_point_lower, padded_point_upper)

        # Then somehow make this list of points into just a sequence of points

        ship_route_polytope = Path(["latitude", "longitude", "step"], initial_shape, *new_points)

        request = Request(
            ship_route_polytope,
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
        )
        result = self.API.retrieve(request)
        result.pprint()

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
            print(i)
        f.close()

        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)

        plt.scatter(lons, lats, s=18, c="red", cmap="YlOrRd")
        plt.scatter(eccodes_lons, eccodes_lats, s=6, c="green")
        plt.colorbar(label="Temperature")
        plt.show()
