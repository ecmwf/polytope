import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Select

# data from https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/download
data = xr.open_dataset('./example_eo/data/sea_ice_data.nc')
print(data)

xarraydatacube = XArrayDatacube(data)
array = data
slicer = HullSlicer()
API = Polytope(datacube=array, engine=slicer)

# create a polytope polyline object to extract
# or take shapefile from https://geodata.lib.utexas.edu/catalog/stanford-wz014rh6670

shapefile = gpd.read_file("./example_eo/data/ice20000410.shp")
ice_block = shapefile.iloc[2]
print(ice_block)
polygon_shp = ice_block["geometry"]

xx, yy = polygon_shp.exterior.coords.xy
polygon_points = [list(a) for a in zip(xx, yy)]

# initial_shape = Box(["latitude", "longitude"], [0, 0], [2, 2])
polygon = Polygon(["longitude", "latitude"], polygon_points)

request = Request(polygon, Select("time", [pd.Timestamp("2020-12-31 12:00:00")]))

# Extract the values of the long and lat from the tree
result = API.retrieve(request)
country_points_plotting = []
lats = []
longs = []
temps = []
print(len(result.leaves))
for i in range(len(result.leaves)):
    cubepath = result.leaves[i].flatten()
    lat = cubepath["latitude"]
    long = cubepath["longitude"]
    latlong_point = [lat, long]
    lats.append(lat)
    longs.append(long)
    t_idx = result.leaves[i].result["sithick"].item()
    t = t_idx
    print(t)
    temps.append(t)
    country_points_plotting.append(latlong_point)
temps = np.array(temps)

worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)
# For multipolygon country
plt.plot(*polygon_shp.exterior.xy, color="black", linewidth=0.7)

plt.scatter(longs, lats, s=8, c=temps, cmap="Blues")
plt.colorbar(label="Sea Ice Thickness")
plt.show()
