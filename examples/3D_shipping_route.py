import math

import geopandas as gpd
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np
from earthkit import data

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Ellipsoid, Path


class Test:
    def setup_method(self):
        ds = data.from_source("file", "./examples/data/winds.grib")
        array = ds.to_xarray()
        array = array.isel(time=0).isel(surface=0).isel(number=0).u10
        self.array = array
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_slice_shipping_route(self):
        shapefile = gpd.read_file("./examples/data/Shipping-Lanes-v1.shp")
        geometry_multiline = shapefile.iloc[2]
        geometry_object = geometry_multiline["geometry"]

        lines = []
        i = 0

        for line in geometry_object[:7]:
            for point in line.coords:
                point_list = list(point)
                if list(point)[0] < 0:
                    point_list[0] = list(point)[0] + 360
                lines.append(point_list)

        speed_km_hr = 100
        initial_distance = math.sqrt(lines[0][0] ** 2 + lines[0][1] ** 2)  # This is technically only the degrees...
        time_hours = [(math.sqrt(pt[0] ** 2 + pt[1] ** 2) - initial_distance) / speed_km_hr for pt in lines]
        step_list_seconds = np.array(time_hours)
        step_list_seconds = step_list_seconds * 3600 * 1000 * 1000 * 1000
        step_list_seconds = [int(a) for a in step_list_seconds]
        step_list = [np.timedelta64(step, "ns") for step in step_list_seconds]

        # Append for each point a corresponding step

        new_points = []
        for point, step in zip(lines[:7], step_list):
            new_points.append([point[1], point[0], step + np.timedelta64(3600000000000, "ns")])

        # Pad the shipping route with an initial shape

        padded_point_upper = [0.24, 0.24, np.timedelta64(3590, "s")]
        padded_point_lower = [-0.24, -0.24, np.timedelta64(-3590, "s")]
        initial_shape = Ellipsoid(["latitude", "longitude", "step"], padded_point_lower, padded_point_upper)

        # Then somehow make this list of points into just a sequence of points

        ship_route_polytope = Path(["latitude", "longitude", "step"], initial_shape, *new_points)
        request = Request(ship_route_polytope)
        result = self.API.retrieve(request)

        # Associate the results to the lat/long points in an array
        lats = []
        longs = []
        parameter_values = []
        winds_u = []
        winds_v = []
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            long = cubepath["longitude"]
            lats.append(lat)
            longs.append(long)

            u10_idx = result.leaves[i].result["u10"]
            wind_u = u10_idx
            v10_idx = result.leaves[i].result["v10"]
            wind_v = v10_idx
            winds_u.append(wind_u)
            winds_v.append(wind_v)
            parameter_values.append(math.sqrt(wind_u**2 + wind_v**2))

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
