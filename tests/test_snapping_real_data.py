# import geopandas as gpd
# import matplotlib.pyplot as plt

import numpy as np
import pytest
from earthkit import data
from helper_functions import download_test_data

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestSlicingEra5Data:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"
        download_test_data(nexus_url, "era5-levels-members.grib")

        ds = data.from_source("file", "./tests/data/era5-levels-members.grib")
        array = ds.to_xarray(engine="cfgrib").isel(step=0).t
        self.slicer = HullSlicer()
        options = {
            "axis_config": [
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "compressed_axes_config": ["longitude", "latitude", "step", "time", "number", "isobaricInhPa"],
        }
        self.API = Polytope(
            datacube=array,
            engine=self.slicer,
            options=options,
        )

    @pytest.mark.internet
    def test_surrounding_on_grid_point(self):
        requested_lat = 0
        requested_lon = -720
        request = Request(
            Box(["number", "isobaricInhPa"], [6, 500.0], [6, 850.0]),
            Select("time", ["2017-01-02T12:00:00"]),
            Select("latitude", [requested_lat], method="surrounding"),
            Select("longitude", [requested_lon], method="surrounding"),
            Select("step", [np.timedelta64(0, "s")]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        country_points_plotting = []
        lats = []
        longs = []
        temps = []
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            long = cubepath["longitude"]
            latlong_point = [lat, long]
            lats.append(lat)
            longs.append(long)
            t_idx = result.leaves[i].result[1]
            temps.append(t_idx)
            country_points_plotting.append(latlong_point)
        temps = np.array(temps)

        # # Plot all the points on a world map
        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # plt.scatter(longs, lats, s=16, c=temps, cmap="YlOrRd")
        # plt.scatter([requested_lon], [requested_lat], s=16, c="blue")
        # plt.colorbar(label="Temperature")
        # plt.show()
        assert len(longs) == 1
        for lon in longs:
            assert lon == (0.0, 3.0, 357.0)
        for lat in lats:
            assert lat == (-3.0, 0.0, 3.0)
