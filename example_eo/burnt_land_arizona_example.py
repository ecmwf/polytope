import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rioxarray

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Disk

# import xarray as xr


# data from https://earthexplorer.usgs.gov, landsat data burnt land

da = rioxarray.open_rasterio('./example_eo/data/burnt_land_landsat.tif', mask=True)
da = da.rio.reproject("EPSG:4326")
df = da[0].to_pandas()
df["y"] = df.index
df = pd.melt(df, id_vars="y")
df.set_index(['x', 'y'], inplace=True)
data = df.to_xarray()

# data is not in lat lon

print(data)

xarraydatacube = XArrayDatacube(data)
array = data
slicer = HullSlicer()
API = Polytope(datacube=array, engine=slicer)

polygon = Disk(["x", "y"], [-111.6, 34.5], [0.015, 0.015])

request = Request(polygon)

print("were here")

# Extract the values of the long and lat from the tree
result = API.retrieve(request)
country_points_plotting = []
lats = []
longs = []
temps = []
print(len(result.leaves))
for i in range(len(result.leaves)):
    cubepath = result.leaves[i].flatten()
    lat = cubepath["y"]
    long = cubepath["x"]
    latlong_point = [lat, long]
    lats.append(lat)
    longs.append(long)
    t_idx = result.leaves[i].result["value"].item()
    t = t_idx
    print(t)
    temps.append(t)
    country_points_plotting.append(latlong_point)
# temps = np.array(temps)

worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)
# For multipolygon country
# plt.plot(*polygon_shp.exterior.xy, color="black", linewidth=0.7)

plt.scatter(longs, lats, s=8, c=temps, cmap="YlOrRd")
plt.colorbar(label="Burnt land")
plt.show()
