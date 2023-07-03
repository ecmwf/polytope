import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from earthkit import data
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file
from matplotlib import markers
from shapely.geometry import shape

from polytope.datacube.octahedral_xarray import OctahedralXArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Union


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
        nearest_index = codes_grib_find_nearest(message, target_lat, target_lon)
        nearest_points.append(nearest_index)

    # Close the GRIB file
    f.close()

    return nearest_points


ds = data.from_source("file", "./foo.grib")
latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
latlon_array = latlon_array.t2m

latlon_xarray_datacube = OctahedralXArrayDatacube(latlon_array)

slicer = HullSlicer()
API = Polytope(datacube=latlon_array, engine=slicer)

shapefile = gpd.read_file("./examples/data/World_Countries__Generalized_.shp")
country = shapefile.iloc[13]
multi_polygon = shape(country["geometry"])
# If country is just a polygon
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
request = Request(request_obj)
result = API.retrieve(request)

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
    eccodes_lats.append(nearest_points[0][0]["lat"])
    eccodes_longs.append(nearest_points[0][0]["lon"])
    t = result.leaves[i].result[1]
    parameter_values.append(t)

parameter_values = np.array(parameter_values)
# Plot this last array according to different colors for the result on a world map
worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
fig, ax = plt.subplots(figsize=(12, 6))
worldmap.plot(color="darkgrey", ax=ax)

marker = markers.MarkerStyle(marker="s")
ax.scatter(eccodes_longs, eccodes_lats, s=12, c="red", marker=marker, facecolors="none")
ax.scatter(longs, lats, s=4, c=parameter_values, cmap="viridis")
norm = mpl.colors.Normalize(vmin=min(parameter_values), vmax=max(parameter_values))

sm = plt.cm.ScalarMappable(cmap="viridis", norm=norm)
sm.set_array([])
plt.colorbar(sm, label="Wind Speed")

plt.show()
