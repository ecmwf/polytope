# import geopandas as gpd
# import matplotlib.pyplot as plt
import pandas as pd
import pytest
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
            "axis_config": [
                {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {"axis_name": "levelist", "transformations": [{"name": "type_change", "type": "int"}]},
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {
                            "name": "mapper",
                            "type": "local_regular",
                            "resolution": [193, 417],
                            "axes": ["latitude", "longitude"],
                            "local": [45.485, 48.1, 5.28985, 10.9087],
                        }
                    ],
                },
            ],
            "pre_path": {"param": "3008"},
            "compressed_axes_config": ["longitude", "latitude", "levtype", "levelist", "step", "date", "param"],
        }

    # Testing different shapes
    @pytest.mark.fdb
    @pytest.mark.skip("Non-accessible data")
    def test_fdb_datacube(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0]),
            Select("levtype", ["unknown"]),
            Select("date", [pd.Timestamp("20211102T120000")]),
            Select("param", ["3008"]),
            Select("levelist", [1]),
            Box(["latitude", "longitude"], [47.38, 7], [47.5, 7.14]),
        )
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        # result.pprint_2()
        assert len(result.leaves) == 99

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-4
        f = open("./tests/data/hhl_geo.grib", "rb")
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
