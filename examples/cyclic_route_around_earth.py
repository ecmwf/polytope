import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, PathSegment


class Test:
    def setup_method(self, method):
        array = xr.open_dataset("./examples/data/output8.grib", engine="cfgrib").t2m
        options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_country(self):
        bounding_box = Box(["latitude", "longitude"], [-0.125, -0.125], [0.125, 0.125])
        request_obj = PathSegment(["latitude", "longitude"], bounding_box, [-88, -719], [88, 720])
        request = Request(request_obj)

        # Extract the values of the long and lat from the tree
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
            # here need to remap the longitude to be between -180 and 180 so that they appear on the map...
            if long < -180:
                long = long + 360
            if -180 <= long < 180:
                long = long
            if 180 <= long < 180 + 360:
                long = long - 360
            if 180 + 360 <= long < 180 + 360 + 360:
                long = long - 720
            latlong_point = [lat, long]
            lats.append(lat)
            longs.append(long)
            t_idx = result.leaves[i].result["t2m"]
            t = t_idx
            temps.append(t)
            country_points_plotting.append(latlong_point)
        temps = np.array(temps)

        # Plot all the points on a world map
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)
        plt.scatter(longs, lats, s=8, c=temps, cmap="YlOrRd")
        plt.colorbar(label="Temperature")
        plt.show()
