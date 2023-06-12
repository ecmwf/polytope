import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, PathSegment

# data from https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/download

data = xr.open_dataset('./example_eo/data/AQUA_MODIS.20020722.L3m.DAY.CHL.chlor_a.9km.nc')
print(data)

options = {"longitude": {"Cyclic": [-180.0, 180.0]}}
for dim in data.dims:
    data = data.sortby(dim)
xarraydatacube = XArrayDatacube(data)
array = data

for dim in array.dims:
    array = array.sortby(dim)
slicer = HullSlicer()
API = Polytope(datacube=array, engine=slicer, options=options)

# Pad the shipping route with an initial shape

padded_point_upper = [2, 2]
padded_point_lower = [1, 1]
initial_shape = Box(["lat", "lon"], padded_point_lower, padded_point_upper)

# Then somehow make this list of points into just a sequence of points

initial_shape = PathSegment(["lat", "lon"], initial_shape, [40.7769, 286.126 - 360], [49.0081, 2.5509])
request = Request(initial_shape)
result = API.retrieve(request)

# Associate the results to the lat/long points in an array

lats = []
longs = []
parameter_values = []
for i in range(len(result.leaves)):
    cubepath = result.leaves[i].flatten()
    lat = cubepath["lat"]
    long = cubepath["lon"]
    lats.append(lat)
    longs.append(long)
    u10_idx = result.leaves[i].result["chlor_a"].item()
    parameter_values.append(u10_idx)

parameter_values = np.array(parameter_values)

# Plot this last array according to different colors for the result on a world map

worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)
plt.scatter(longs[::5], lats[::5], s=8, c=parameter_values[::5], cmap="viridis")
plt.colorbar(label="Chlorophyll level")
plt.show()
