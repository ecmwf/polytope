# NOTE THIS EXAMPLE DOES NOT WORK...

import xarray as xr
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np
import rioxarray
import pandas as pd
from shapely.geometry import shape

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Union

da = rioxarray.open_rasterio('./example_eo/data/mangrove_cover_aus3.tif', mask=True)
da = da.rio.reproject("EPSG:4326")
df = da[0].to_pandas()
df["y"] = df.index
df = pd.melt(df, id_vars="y")
df.set_index(['x', 'y'], inplace=True)
data = df.to_xarray()

# data = xr.open_rasterio('./example_eo/data/mangrove_cover_aus3.tif')
print(data)
# data = data.to_dataset(name="mangrove_cover")
# data_band1 = data.isel(band=1)
# data_band1 = data[dict(x=3199)]
# print(data_band1.values)
data_band1 = data
# data_band1.plot()
# plt.show()

# now use the australia costlines hotspots shapefile
# TODO: here instead take Australian costline shapefile in lat/lon
# shapefile = gpd.read_file("./example_eo/data/DEACoastlines_hotspots_v1.0.0.shp")
shapefile = gpd.read_file("./examples/data/World_Countries__Generalized_.shp")
country = shapefile.iloc[12]
print(shapefile)

multi_polygon = shape(country["geometry"])
multi_polygon = multi_polygon.buffer(distance=0.015)
        # If country is a multipolygon
polygons = list(multi_polygon.geoms)
        # If country is just a polygon
        # polygons = [multi_polygon]
polygons_list = []

        # Now create a list of x,y points for each polygon

for polygon in polygons:
    xx, yy = polygon.exterior.coords.xy
    polygon_points = [list(a) for a in zip(xx, yy)]
    polygons_list.append(polygon_points)

        # Then do union of the polygon objects and cut using the slicer
poly = []
for points in polygons_list:
    polygon = Polygon(["x", "y"], points)
    poly.append(polygon)
request_obj = poly[0]
for obj in poly:
    request_obj = Union(["x", "y"], request_obj, obj)
request = Request(request_obj)


# create a list of all the points in the shapefile

# points = shapefile.geometry.values
# array_points = [[-point.coords[0][0], point.coords[0][1]] for point in points[100:130]]
# print(array_points)
# print(data)

# # create a polytope polyline object from these points

# initial_shape = Box(["x", "y"], [0, 0], [2, 2])
# australia_coastline = Path(["x", "y"], initial_shape, *array_points)

# extract this shape from the mangrove cover datacube
# first create the mangrove datacube

xarraydatacube = XArrayDatacube(data)
array = data
slicer = HullSlicer()
API = Polytope(datacube=array, engine=slicer)

# then extract shape

# request = Request(australia_coastline, Select("band", [1]))
request = Request(polygon)
print("here")
result = API.retrieve(request)
# result.pprint()
print("here")

# and plot result

xs = []
ys = []

parameter_values = []
print(len(result.leaves))
for i in range(len(result.leaves)):
    print(i)
    cubepath = result.leaves[i].flatten()
    x = cubepath["x"]
    y = cubepath["y"]
    xs.append(x)
    ys.append(y)
    # print(result.leaves[i].result)
    parameter_values.append(result.leaves[i].result["mangrove_cover"].item())
parameter_values = np.array(parameter_values)
worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)
# For multipolygon country
for geom in multi_polygon.geoms:
    plt.plot(*geom.exterior.xy, color="black", linewidth=0.7)
plt.scatter(xs, ys, c=parameter_values, cmap="Reds")
plt.show()
