import pandas as pd
import pytest
from helper_functions import download_test_data, find_nearest_latlon

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Disk, Select

# import geopandas as gpd
# import matplotlib.pyplot as plt


class TestRegularGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")
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
                        {
                            "name": "mapper",
                            "type": "regular",
                            "resolution": 30,
                            "axes": ["latitude", "longitude"],
                            "axis_reversed": {"latitude": True, "longitude": False},
                            "md5_hash": "15372eaafa9d744000df708d63f69284",
                        }
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "pre_path": {"class": "ea", "expver": "0001", "levtype": "pl", "step": "0"},
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
                "levelist",
            ],
        }

    @pytest.mark.fdb
    @pytest.mark.internet
    def test_regular_grid(self):
        import pygribjump as gj

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
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 3
        assert len(result.leaves[0].result) == 2
        assert len(result.leaves[1].result) == 6
        assert len(result.leaves[2].result) == 2
        assert len(result.leaves[0].values) == 1
        assert len(result.leaves[1].values) == 3
        assert len(result.leaves[2].values) == 1

        from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.regular import (
            RegularGridMapper,
        )

        lats = []
        lons = []
        eccodes_lats = []
        tol = 1e-8
        leaves = result.leaves
        for i in range(len(leaves)):
            right_pl_results = leaves[i].result[len(leaves[i].values) :]
            result_tree = right_pl_results[0]
            cubepath = leaves[i].flatten()
            lat = cubepath["latitude"][0]
            lon = cubepath["longitude"][0]
            lats.append(lat)
            lons.append(lon)
            nearest_points = find_nearest_latlon("./tests/data/era5-levels-members.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_value = nearest_points[121][0]["value"]
            eccodes_lats.append(eccodes_lat)

            mapper = RegularGridMapper("base", ["base1", "base2"], 30)
            assert nearest_points[121][0]["index"] == mapper.unmap((lat,), (lon,))[0]

            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol
            assert eccodes_value == result_tree

        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(lons, lats, s=16, c="red", cmap="YlOrRd")
        # plt.colorbar(label="Temperature")
        # plt.show()

        assert len(eccodes_lats) == 3
