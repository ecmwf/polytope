import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from shapely.geometry import shape

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Union


class Test():

    def setup_method(self, method):
        array = xr.open_dataset(".examples/data/output8.grib", engine='cfgrib')
        options = {"longitude" : {"Cyclic" : [0, 360.]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_country(self):

        # Read a shapefile for a given country and extract the geometry polygons
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)
        whole_lat_old = np.arange(-90., 90., 0.125)
        whole_long_old = np.arange(-180, 180, 0.125)
        whole_lat = np.repeat(whole_lat_old, len(whole_long_old))
        whole_long = np.tile(whole_long_old, len(whole_lat_old))
        countries_lats = []
        countries_longs = []
        countries_temps = []
        country_points_plotting = []

        plt.scatter(whole_long, whole_lat, s=1, alpha=0.25, color="wheat")

        # Shapefile taken from
        # https://hub.arcgis.com/datasets/esri::world-countries-generalized/explore?location=-0.131595%2C0.000000%2C2.00
        shapefile = gpd.read_file("./examples/data/World_Countries__Generalized_.shp")
        country = shapefile
        shapefile = shapefile.set_index("COUNTRY")

        ECMWF_country_list_multipolygon = ["Croatia", "Denmark", "Estonia", "Finland", "France", "Germany", "Greece",
                                           "Ireland", "Italy", "Netherlands", "Norway", "Spain", "Sweden", "Turkiye",
                                           "United Kingdom"]
        ECMWF_country_list_polygon = ["Austria", "Belgium", "Iceland", "Luxembourg", "Portugal", "Serbia", "Slovenia",
                                      "Switzerland"]

        for country_name_polygon in ECMWF_country_list_polygon:
            country = shapefile.loc[country_name_polygon]
            multi_polygon = shape(country["geometry"])
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
            request = Request(request_obj)

            # Extract the values of the long and lat from the tree
            result = self.API.retrieve(request)
            for i in range(len(result.leaves)):
                cubepath = result.leaves[i].flatten()
                lat = cubepath["latitude"]
                long = cubepath["longitude"]
                if long >= 180:
                    long = long - 360
                latlong_point = [lat, long]
                countries_lats.append(lat)
                countries_longs.append(long)
                t_idx = result.leaves[i].result["t2m"]
                t = t_idx
                countries_temps.append(t)
                country_points_plotting.append(latlong_point)

            # Plot all the points on a world map
            plt.plot(*multi_polygon.exterior.xy, color="black", linewidth=0.7)

        for country_name_multipolygon in ECMWF_country_list_multipolygon:
            country = shapefile.loc[country_name_multipolygon]
            multi_polygon = shape(country["geometry"])
            polygons = list(multi_polygon.geoms)
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

            request = Request(request_obj)

            # Extract the values of the long and lat from the tree
            result = self.API.retrieve(request)
            for i in range(len(result.leaves)):
                cubepath = result.leaves[i].flatten()
                lat = cubepath["latitude"]
                long = cubepath["longitude"]
                if long >= 180:
                    long = long - 360
                latlong_point = [lat, long]
                countries_lats.append(lat)
                countries_longs.append(long)
                t_idx = result.leaves[i].result["t2m"]
                t = t_idx
                countries_temps.append(t)
                country_points_plotting.append(latlong_point)

            # Plot all the points on a world map

            for geom in multi_polygon.geoms:
                plt.plot(*geom.exterior.xy, color="black", linewidth=0.7)
        countries_temps = np.array(countries_temps)
        plt.scatter(countries_longs, countries_lats, s=8, c=countries_temps, cmap="YlOrRd")
        plt.colorbar(label="Temperature")

        plt.show()
