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
from polytope.shapes import Disk, PathSegment

# data taken from https://land.copernicus.eu/pan-european/high-resolution-layers/forests/tree-cover-density/status-maps/tree-cover-density-2018?tab=download
# data = xr.open_rasterio('./example_eo/data/tree_cover_germany.tif')
da = rioxarray.open_rasterio('./example_eo/data/tree_cover_germany.tif', masked=True)
da = da.rio.reproject("EPSG:4326")
df = da[0].to_pandas()
df["y"] = df.index
df = pd.melt(df, id_vars="y")
df.set_index(['x', 'y'], inplace=True)

data = df.to_xarray()

print(data)
# print(data.attrs)

initial_shape = Disk(["x", "y"], [0,0], [0.015, 0.015])

        # Then somehow make this list of points into just a sequence of points

request_obj = PathSegment(["x", "y"], initial_shape, [5.75, 48.55], [5.8, 48.6])
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
# request = Request(polygon)
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
    print(result.leaves[i].result)
    parameter_values.append(result.leaves[i].result["value"].item())
parameter_values = np.array(parameter_values)
worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)
# For multipolygon country
# for geom in multi_polygon.geoms:
#     plt.plot(*geom.exterior.xy, color="black", linewidth=0.7)
plt.scatter(xs, ys, c=parameter_values, cmap="Greens")
plt.show()
