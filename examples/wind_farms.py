import math

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr
from osgeo import gdal
from shapely.geometry import shape

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Select, Union


class Test():

    def setup_method(self):
        array = xr.open_dataset("./examples/data/winds.grib", engine='cfgrib')
        self.array = array
        options = {"longitude" : {"Cyclic" : [0, 360.]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_shipping_route(self):
        gdal.SetConfigOption('SHAPE_RESTORE_SHX', 'YES')

        shapefile = gpd.read_file("./examples/data/EMODnet_HA_WindFarms_pg_20220324.shp")
        polygons = []
        for i in range(306):
            country = shapefile.iloc[i]
            multi_polygon = shape(country["geometry"])
            if multi_polygon.geom_type == 'MultiPolygon':
                true_polygons = list(multi_polygon.geoms)
                for true_polygon in true_polygons:
                    polygons.append(true_polygon)
            else:
                polygons.append(multi_polygon)
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
                          Select("step", [np.timedelta64(0, "ns")]))

        # Extract the values of the long and lat from the tree
        result = self.API.retrieve(request)
        lats = []
        longs = []
        parameter_values = []
        winds_u = []
        winds_v = []
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            long = cubepath["longitude"]
            if long < -180:
                long = long + 360
            if long > 180:
                long = long - 360
            lats.append(lat)
            longs.append(long)
            u10_idx = result.leaves[i].result["u10"]
            wind_u = u10_idx
            v10_idx = result.leaves[i].result["v10"]
            wind_v = v10_idx
            winds_u.append(wind_u)
            winds_v.append(wind_v)
            parameter_values.append(math.sqrt(wind_u**2 + wind_v**2))

        parameter_values = np.array(parameter_values)
        # Plot this last array according to different colors for the result on a world map
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)
        ax.scatter(longs, lats, s=8, c=parameter_values, cmap="viridis")
        norm = mpl.colors.Normalize(vmin=min(parameter_values), vmax=max(parameter_values))

        sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
        sm.set_array([])
        plt.colorbar(sm, label="Wind Speed")

        plt.show()
