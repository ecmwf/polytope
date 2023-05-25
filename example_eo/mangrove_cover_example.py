# NOTE THIS EXAMPLE DOES NOT WORK...

import xarray as xr
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Path, Select

data = xr.open_rasterio('./example_eo/data/mangrove_cover_aus3.tif')
print(data)
data = data.to_dataset(name="mangrove_cover")
# data_band1 = data.isel(band=1)
# data_band1 = data[dict(x=3199)]
# print(data_band1.values)
data_band1 = data
# data_band1.plot()
# plt.show()

# now use the australia costlines hotspots shapefile

shapefile = gpd.read_file("./example_eo/data/DEACoastlines_hotspots_v1.0.0.shp")
print(shapefile)

# create a list of all the points in the shapefile

points = shapefile.geometry.values
array_points = [[-point.coords[0][0], point.coords[0][1]] for point in points[100:130]]
print(array_points)
print(data)

# create a polytope polyline object from these points

initial_shape = Box(["x", "y"], [0, 0], [2, 2])
australia_coastline = Path(["x", "y"], initial_shape, *array_points)

# extract this shape from the mangrove cover datacube
# first create the mangrove datacube

xarraydatacube = XArrayDatacube(data)
array = data
slicer = HullSlicer()
API = Polytope(datacube=array, engine=slicer)

# then extract shape

request = Request(australia_coastline, Select("band", [1]))
result = API.retrieve(request)
result.pprint()

# and plot result

xs = []
ys = []

parameter_values = []
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
plt.scatter(xs, ys, c=parameter_values, cmap="Reds")
data = xr.open_rasterio('./example_eo/data/mangrove_cover_aus3.tif')
data = data.where(data.x > 1569245, drop=True)
data.where(data.x < 1575015, drop=True)
data.where(data.y < -2300895, drop=True)
data = data.where(data.y > -2403715, drop=True)
data.plot()
plt.show()
