# import geopandas as gpd
# import matplotlib.pyplot as plt
import numpy as np
from earthkit import data

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingEra5Data:
    def setup_method(self, method):
        ds = data.from_source("file", "./tests/data/era5-levels-members.grib")
        array = ds.to_xarray().isel(step=0).t
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        options = {"latitude": {"transformation": {"reverse": {True}}},
                   "longitude": {"transformation": {"cyclic": [0, 360.0]}}}
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    def test_surrounding_on_grid_point(self):
        requested_lat = 0
        requested_lon = 0
        request = Request(
            Box(["number", "isobaricInhPa"], [6, 500.0], [6, 850.0]),
            Select("time", ["2017-01-02T12:00:00"]),
            # Box(["latitude", "longitude"], lower_corner=[0.0, 0.0], upper_corner=[10.0, 30.0]),
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
        for lon in longs:
            assert lon in [-3, 0, 3]
