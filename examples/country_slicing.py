import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
from earthkit import data
from shapely.geometry import shape

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Select, Union


class Test:
    def setup_method(self, method):
        ds = data.from_source("file", "./examples/data/output8.grib")
        array = ds.to_xarray()
        array = array.isel(surface=0).isel(step=0).isel(number=0).isel(time=0).t2m
        print(array)
        options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_country(self):
        # Read a shapefile for a given country and extract the geometry polygons

        # Shapefile taken from
        # https://hub.arcgis.com/datasets/esri::world-countries-generalized/explore?location=-0.131595%2C0.000000%2C2.00
        shapefile = gpd.read_file("./examples/data/World_Countries__Generalized_.shp")
        country = shapefile.iloc[13]
        multi_polygon = shape(country["geometry"])
        # If country is a multipolygon
        # polygons = list(multi_polygon.geoms)
        # If country is just a polygon
        polygons = [multi_polygon]
        polygons_list = []

        # Now create a list of x,y points for each polygon

        for polygon in polygons:
            xx, yy = polygon.exterior.coords.xy
            polygon_points = [list(a) for a in zip(xx, yy)]
            polygons_list.append(polygon_points)

        # Then do union of the polygon objects and cut using the slicer
        poly = []
        for points in polygons_list:
            polygon = Polygon(["longitude", "latitude"], points)
            poly.append(polygon)
        request_obj = poly[0]
        for obj in poly:
            request_obj = Union(["longitude", "latitude"], request_obj, obj)
        request = Request(request_obj,
                          Select("number", [0]),
                          Select("time", ["2022-02-06T12:00:00"]),
                          Select("step", ["00:00:00"]),
                          Select("surface", [0]),
                          Select("valid_time", ["2022-02-06T12:00:00"]))

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
            t_idx = result.leaves[i].result[1]
            temps.append(t_idx)
            country_points_plotting.append(latlong_point)
        temps = np.array(temps)

        # Plot all the points on a world map
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)

        # For multipolygon country
        # for geom in multi_polygon.geoms:
        #     plt.plot(*geom.exterior.xy, color="black", linewidth=0.7)
        # For polygon country
        for geom in [multi_polygon]:
            plt.plot(*geom.exterior.xy, color="black", linewidth=0.7)

        whole_lat_old = np.arange(-90.0, 90.0, 0.125)
        whole_long_old = np.arange(-180, 180, 0.125)
        whole_lat = np.repeat(whole_lat_old, len(whole_long_old))
        whole_long = np.tile(whole_long_old, len(whole_lat_old))

        plt.scatter(whole_long, whole_lat, s=1, alpha=0.25, color="wheat")
        plt.scatter(longs, lats, s=8, c=temps, cmap="YlOrRd")
        plt.colorbar(label="Temperature")
        plt.show()
