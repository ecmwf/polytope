import geopandas as gpd
import numpy as np
from earthkit import data
from shapely.geometry import shape

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Polygon, Select, Union


class Test:
    def setup_method(self):
        ds = data.from_source("file", "./examples/data/timeseries_t2m.grib")
        array = ds.to_xarray()
        array = array.isel(step=0).isel(surface=0).isel(number=0).t2m
        self.xarraydatacube = XArrayDatacube(array)
        for dim in array.dims:
            array = array.sortby(dim)
        self.array = array
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_slice_shipping_route(self):
        shapefile = gpd.read_file("./examples/data/World_Countries__Generalized_.shp")
        country = shapefile.iloc[57]
        multi_polygon = shape(country["geometry"])
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
            polygon = Polygon(["longitude", "latitude"], points)
            poly.append(polygon)

        request_obj = poly[0]

        for obj in poly:
            request_obj = Union(["longitude", "latitude"], request_obj, obj)

        request = Request(
            request_obj,
            Select("time", [np.datetime64("2022-05-14T12:00:00")]),
            Select("number", [0]),
            Select("step", ["00:00:00"]),
            Select("surface", [0]),
        )

        result = self.API.retrieve(request)

        result.pprint()

        # For each date/time, we plot an image
        # Note that only the temperatures should change so we can store them in different arrays

        """
        country_points_plotting = []
        lats1 = []
        lats2 = []
        lats3 = []
        lats4 = []
        lats5 = []
        lats6 = []
        lats7 = []
        lats8 = []
        longs1 = []
        longs2 = []
        longs3 = []
        longs4 = []
        longs5 = []
        longs6 = []
        longs7 = []
        longs8 = []
        temps1 = []
        temps2 = []
        temps3 = []
        temps4 = []
        temps5 = []
        temps6 = []
        temps7 = []
        temps8 = []
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            long = cubepath["longitude"]
            latlong_point = [lat, long]
            t_idx = result.leaves[i].result[1]
            if cubepath["time"] == pd.Timestamp("2022-05-14T12:00:00"):
                temps1.append(t_idx)
                lats1.append(lat)
                longs1.append(long)
            if cubepath["time"] == pd.Timestamp("2022-06-14T12:00:00"):
                temps2.append(t_idx)
                lats2.append(lat)
                longs2.append(long)
            if cubepath["time"] == pd.Timestamp("2022-07-14T12:00:00"):
                temps3.append(t_idx)
                lats3.append(lat)
                longs3.append(long)
            if cubepath["time"] == pd.Timestamp("2022-08-14T12:00:00"):
                temps4.append(t_idx)
                lats4.append(lat)
                longs4.append(long)
            if cubepath["time"] == pd.Timestamp("2022-09-14T12:00:00"):
                temps5.append(t_idx)
                lats5.append(lat)
                longs5.append(long)
            if cubepath["time"] == pd.Timestamp("2022-10-14T12:00:00"):
                temps6.append(t_idx)
                lats6.append(lat)
                longs6.append(long)
            if cubepath["time"] == pd.Timestamp("2022-11-14T12:00:00"):
                temps7.append(t_idx)
                lats7.append(lat)
                longs7.append(long)
            if cubepath["time"] == pd.Timestamp("2022-12-14T12:00:00"):
                temps8.append(t_idx)
                lats8.append(lat)
                longs8.append(long)
            country_points_plotting.append(latlong_point)

        temps1 = np.array(temps1)
        temps2 = np.array(temps2)
        temps3 = np.array(temps3)
        temps4 = np.array(temps4)
        temps5 = np.array(temps5)
        temps6 = np.array(temps6)
        temps7 = np.array(temps7)
        temps8 = np.array(temps8)

        # Plot all the points on a world map

        fig, ax = plt.subplots(4, 2, sharex=True, sharey=True, figsize=(18, 9))

        # For multipolygon country
        for geom in multi_polygon.geoms:
            ax[0, 0].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[0, 1].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[1, 0].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[1, 1].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[2, 0].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[2, 1].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[3, 0].plot(*geom.exterior.xy, color="black", linewidth=0.7)
            ax[3, 1].plot(*geom.exterior.xy, color="black", linewidth=0.7)

        minmin = np.min(
            [
                np.min(temps1),
                np.min(temps2),
                np.min(temps3),
                np.min(temps4),
                np.min(temps5),
                np.min(temps6),
                np.min(temps7),
                np.min(temps8),
            ]
        )
        maxmax = np.max(
            [
                np.max(temps1),
                np.max(temps2),
                np.max(temps3),
                np.max(temps4),
                np.max(temps5),
                np.max(temps6),
                np.max(temps7),
                np.max(temps8),
            ]
        )
        ax[0, 0].scatter(longs1, lats1, s=8, vmin=minmin, vmax=maxmax, c=temps1, cmap="YlOrRd")
        ax[0, 1].scatter(longs2, lats2, s=8, vmin=minmin, vmax=maxmax, c=temps2, cmap="YlOrRd")
        ax[1, 0].scatter(longs3, lats3, s=8, vmin=minmin, vmax=maxmax, c=temps3, cmap="YlOrRd")
        ax[1, 1].scatter(longs4, lats4, s=8, vmin=minmin, vmax=maxmax, c=temps4, cmap="YlOrRd")
        ax[2, 0].scatter(longs5, lats5, s=8, vmin=minmin, vmax=maxmax, c=temps5, cmap="YlOrRd")
        ax[2, 1].scatter(longs6, lats6, s=8, vmin=minmin, vmax=maxmax, c=temps6, cmap="YlOrRd")
        ax[3, 0].scatter(longs7, lats7, s=8, vmin=minmin, vmax=maxmax, c=temps7, cmap="YlOrRd")
        ax[3, 1].scatter(longs8, lats8, s=8, vmin=minmin, vmax=maxmax, c=temps8, cmap="YlOrRd")

        ax[0, 0].set_yticklabels([])
        ax[0, 0].set_xticklabels([])
        ax[0, 1].set_yticklabels([])
        ax[0, 1].set_xticklabels([])
        ax[1, 0].set_yticklabels([])
        ax[1, 0].set_xticklabels([])
        ax[1, 1].set_yticklabels([])
        ax[1, 1].set_xticklabels([])
        ax[2, 0].set_yticklabels([])
        ax[2, 0].set_xticklabels([])
        ax[2, 1].set_yticklabels([])
        ax[2, 1].set_xticklabels([])
        ax[3, 0].set_yticklabels([])
        ax[3, 0].set_xticklabels([])
        ax[3, 1].set_yticklabels([])
        ax[3, 1].set_xticklabels([])

        ax[0, 0].set_yticks([])
        ax[0, 0].set_xticks([])
        ax[0, 1].set_yticks([])
        ax[0, 1].set_xticks([])
        ax[1, 0].set_yticks([])
        ax[1, 0].set_xticks([])
        ax[1, 1].set_yticks([])
        ax[1, 1].set_xticks([])
        ax[2, 0].set_yticks([])
        ax[2, 0].set_xticks([])
        ax[2, 1].set_yticks([])
        ax[2, 1].set_xticks([])
        ax[3, 0].set_yticks([])
        ax[3, 0].set_xticks([])
        ax[3, 1].set_yticks([])
        ax[3, 1].set_xticks([])
        plt.gca().axes.get_yaxis().set_visible(False)
        plt.show()
        """
