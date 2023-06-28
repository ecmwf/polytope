import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from earthkit import data

from polytope.datacube.octahedral_xarray import OctahedralXArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box

ds = data.from_source("file", "./foo.grib")
latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
latlon_array = latlon_array.t2m

latlon_xarray_datacube = OctahedralXArrayDatacube(latlon_array)

slicer = HullSlicer()
API = Polytope(datacube=latlon_array, engine=slicer)

request = Request(Box(["latitude", "longitude"], [3, 3], [5, 5]))
result = API.retrieve(request)
result.pprint()

request2 = Request(Box(["latitude", "longitude"], [70, 3], [72, 5]))
result2 = API.retrieve(request2)
result2.pprint()

lats = []
longs = []
parameter_values = []
for i in range(len(result.leaves)):
    cubepath = result.leaves[i].flatten()
    lat = cubepath["latitude"]
    long = cubepath["longitude"]
    lats.append(lat)
    longs.append(long)

    t = result.leaves[i].result[1]
    parameter_values.append(t)

for i in range(len(result2.leaves)):
    cubepath = result2.leaves[i].flatten()
    lat = cubepath["latitude"]
    long = cubepath["longitude"]
    lats.append(lat)
    longs.append(long)

    t = result2.leaves[i].result[1]
    parameter_values.append(t)

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
