import geopandas as gpd
import matplotlib.pyplot as plt
from earthkit import data
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestOctahedralGrid:
    def setup_method(self, method):
        ds = data.from_source("file", "./tests/data/healpix.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(time=0).isel(isobaricInhPa=0).z
        self.xarraydatacube = XArrayDatacube(self.latlon_array)
        self.options = {
            "values": {
                "transformation": {"mapper": {"type": "healpix", "resolution": 32, "axes": ["latitude", "longitude"]}}
            }
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.latlon_array, engine=self.slicer, axis_options=self.options)

    def find_nearest_latlon(self, grib_file, target_lat, target_lon):
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

    def test_octahedral_grid(self):
        request = Request(
            Box(["latitude", "longitude"], [-2, -2], [10, 10]),
            Select("time", ["2022-12-14T12:00:00"]),
            Select("step", ["01:00:00"]),
            Select("isobaricInhPa", [500]),
            Select("valid_time", ["2022-12-14T13:00:00"]),
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 35

        lats = []
        lons = []
        eccodes_lats = []
        eccodes_lons = []
        tol = 1e-8
        for i in range(len(result.leaves)):
            cubepath = result.leaves[i].flatten()
            lat = cubepath["latitude"]
            lon = cubepath["longitude"]
            lats.append(lat)
            lons.append(lon)
            nearest_points = self.find_nearest_latlon("./tests/data/healpix.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol
        assert len(eccodes_lats) == 35
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="darkgrey", ax=ax)

        plt.scatter(eccodes_lons, eccodes_lats, c="blue", marker="s", s=20)
        plt.scatter(lons, lats, s=16, c="red", cmap="YlOrRd")
        plt.colorbar(label="Temperature")
        plt.show()
