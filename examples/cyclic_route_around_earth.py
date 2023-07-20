import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from earthkit import data

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, PathSegment


class Test:
    def setup_method(self, method):
        ds = data.from_source("file", ".examples/data/output8.grib")
        array = ds.to_xarray()
        array = array.isel(surface=0).isel(step=0).isel(number=0).isel(time=0).t2m
        axis_options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=axis_options)

    def test_slice_country(self):
        bounding_box = Box(["latitude", "longitude"], [-0.1, -0.1], [0.1, 0.1])
        request_obj = PathSegment(["latitude", "longitude"], bounding_box, [-88, -67], [68, 170])
        request = Request(request_obj)

        # Extract the values of the long and lat from the tree
        result = self.API.retrieve(request)
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
            t_idx = result.leaves[i].result["t2m"]
            temps.append(t_idx)
            country_points_plotting.append(latlong_point)
        temps = np.array(temps)

        # Plot all the points on a world map
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)
        plt.scatter(longs, lats, s=8, c=temps, cmap="YlOrRd")
        plt.colorbar(label="Temperature")
        plt.show()
