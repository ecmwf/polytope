import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from earthkit import data

from polytope.datacube.octahedral_xarray import OctahedralXArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box

from eccodes import *


def find_nearest_latlon(grib_file, target_lat, target_lon):
    # Open the GRIB file
    f = open(grib_file)

    # Load the GRIB messages from the file
    messages = []
    while True:
        message = codes_grib_new_from_file(f)
        if message is None:
            break
        messages.append(message)

    # Find the nearest grid points
    nearest_points = []
    for message in messages:
        # latitudes = codes_get_array(message, "latitudes")
        # longitudes = codes_get_array(message, "longitudes")
        # nearest_index = codes_grib_find_nearest(message, target_lat, target_lon, latitudes, longitudes)
        nearest_index = codes_grib_find_nearest(message, target_lat, target_lon)
        print(nearest_index)
        # nearest_points.append((latitudes[nearest_index], longitudes[nearest_index]))
        nearest_points.append(nearest_index)

    # Close the GRIB file
    f.close()

    return nearest_points

ds = data.from_source("file", "./foo.grib")
latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
latlon_array = latlon_array.t2m
# print([val for val in latlon_array["latitude"].values[:] if val>0][-1])

latlon_xarray_datacube = OctahedralXArrayDatacube(latlon_array)

slicer = HullSlicer()
API = Polytope(datacube=latlon_array, engine=slicer)

request = Request(Box(["latitude", "longitude"], [89, -1], [89.5, 181]))
result = API.retrieve(request)
result.pprint()

request2 = Request(Box(["latitude", "longitude"], [70, 3], [72, 5]))
result2 = API.retrieve(request2)
result2.pprint()

lats = []
longs = []
eccodes_lats = []
eccodes_longs = []
parameter_values = []
for i in range(len(result.leaves)):
    cubepath = result.leaves[i].flatten()
    lat = cubepath["latitude"]
    long = cubepath["longitude"]
    lats.append(lat)
    longs.append(long)
    nearest_points = find_nearest_latlon("./foo.grib", lat, long)
    print(nearest_points)
    eccodes_lats.append(nearest_points[0][0]["lat"])
    eccodes_longs.append(nearest_points[0][0]["lon"])

    t = result.leaves[i].result[1]
    parameter_values.append(t)

# for i in range(len(result2.leaves)):
#     cubepath = result2.leaves[i].flatten()
#     lat = cubepath["latitude"]
#     long = cubepath["longitude"]
#     lats.append(lat)
#     longs.append(long)

#     t = result2.leaves[i].result[1]
#     parameter_values.append(t)

parameter_values = np.array(parameter_values)
# Plot this last array according to different colors for the result on a world map
worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)
from matplotlib import markers
marker = markers.MarkerStyle(marker='s')
ax.scatter(eccodes_longs, eccodes_lats, s=12, c="red", marker=marker, facecolors='none')
ax.scatter(longs, lats, s=4, c=parameter_values, cmap="viridis")
norm = mpl.colors.Normalize(vmin=min(parameter_values), vmax=max(parameter_values))

sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
sm.set_array([])
plt.colorbar(sm, label="Wind Speed")

plt.show()


# grib_file = "./foo.grib"
# target_lat = 40.0
# target_lon = -100.0

# nearest_points = find_nearest_latlon(grib_file, target_lat, target_lon)
# print(nearest_points)