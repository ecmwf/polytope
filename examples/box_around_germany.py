import geopandas as gpd
import matplotlib.pyplot as plt
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box


def format_stats_nicely(stats):
    for key in stats.keys():
        print(key)
        print("-----------------------" + "\n")
        actual_stats = stats[key]
        actual_stats_keys = list(actual_stats.keys())
        print(str(actual_stats_keys[0]) + "\t" + str(actual_stats_keys[1]) + "\t" + str(actual_stats_keys[2])
              + "\t" + str(actual_stats_keys[3]))
        print(str(actual_stats[actual_stats_keys[0]]) + "\t" + str(actual_stats[actual_stats_keys[1]]) + "\t"
              + str(actual_stats[actual_stats_keys[2]]) + "\t" + str(actual_stats[actual_stats_keys[3]]))
        print("\n")


class Test:
    def setup_method(self, method):
        array = xr.open_dataset("./examples/data/output8.grib", engine="cfgrib")
        options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_country(self):
        request_obj = Box(["latitude", "longitude"], [47.25, 6], [55, 15])
        request = Request(request_obj)

        # Extract the values of the long and lat from the tree
        result, stats = self.API.retrieve_debugging(request)
        # result.pprint()
        print("stats")
        print("=====================")
        print("\n")
        format_stats_nicely(stats)
        # country_points_plotting = []
        # lats = []
        # longs = []
        # temps = []
        # for i in range(len(result.leaves)):
        #     cubepath = result.leaves[i].flatten()
        #     lat = cubepath["latitude"]
        #     long = cubepath["longitude"]
        #     if long >= 180:
        #         long = long - 360
        #     latlong_point = [lat, long]
        #     lats.append(lat)
        #     longs.append(long)
        #     # print(result.leaves[i])
        #     t_idx = result.leaves[i].result["t2m"]
        #     t = t_idx
        #     temps.append(t)
        #     country_points_plotting.append(latlong_point)
        # # temps = np.array(temps)

        # print(len(lats))
        # print((max(lats)-min(lats))*(max(longs)-min(longs))*8*8)

        # # Plot all the points on a world map
        # worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        # fig, ax = plt.subplots(figsize=(12, 6))
        # worldmap.plot(color="darkgrey", ax=ax)

        # # For multipolygon country
        # for geom in multi_polygon.geoms:
        #     plt.plot(*geom.exterior.xy, color="black", linewidth=0.7)

        # # whole_lat_old = np.arange(-90.0, 90.0, 0.125)
        # # whole_long_old = np.arange(-180, 180, 0.125)
        # # whole_lat = np.repeat(whole_lat_old, len(whole_long_old))
        # # whole_long = np.tile(whole_long_old, len(whole_lat_old))

        # # plt.scatter(whole_long, whole_lat, s=1, alpha=0.25, color="wheat")
        # # plt.scatter(longs, lats, s=8, c=temps, cmap="YlOrRd")
        # plt.scatter(longs, lats, s=8)
        # plt.colorbar(label="Temperature")
        # plt.show()
