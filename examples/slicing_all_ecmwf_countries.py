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
        options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_country(self):
        # Read a shapefile for a given country and extract the geometry polygons
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)
        countries_lats = []
        countries_longs = []
        countries_temps = []
        country_points_plotting = []

        # Shapefile taken from
        # https://hub.arcgis.com/datasets/esri::world-countries-generalized/explore?location=-0.131595%2C0.000000%2C2.00
        shapefile = gpd.read_file("./examples/data/World_Countries__Generalized_.shp")

        ECMWF_country_list_multipolygon = [
            57,
            62,
            71,
        ]
        ECMWF_country_list_polygon = [
            13,
            21,
        ]

        for country_name_polygon in ECMWF_country_list_polygon:
            country = shapefile.iloc[country_name_polygon]
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
            request = Request(request_obj,
                              Select("number", [0]),
                              Select("time", ["2022-02-06T12:00:00"]),
                              Select("step", ["00:00:00"]),
                              Select("surface", [0]),
                              Select("valid_time", ["2022-02-06T12:00:00"]))

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
            country = shapefile.iloc[country_name_multipolygon]
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

            request = Request(request_obj,
                              Select("number", [0]),
                              Select("time", ["2022-02-06T12:00:00"]),
                              Select("step", ["00:00:00"]),
                              Select("surface", [0]),
                              Select("valid_time", ["2022-02-06T12:00:00"]))

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
                t_idx = result.leaves[i].result[1]
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
