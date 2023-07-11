from earthkit import data
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file

from polytope.datacube.octahedral_xarray import OctahedralXArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box


class TestOctahedralGrid:
    def setup_method(self, method):
        ds = data.from_source("file", "./foo.grib")
        latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        latlon_array = latlon_array.t2m
        self.xarraydatacube = OctahedralXArrayDatacube(latlon_array)
        grid_options = {"values" : {"grid_map" : {"type" : ["octahedral", 1280], "axes" : ["latitude", "longitude"]}}}
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=latlon_array, engine=self.slicer, grid_options=grid_options)

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
        request = Request(Box(["latitude", "longitude"], [0, 0], [0.5, 0.5]))
        result = self.API.retrieve(request)
        assert len(result.leaves) == 56

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
            nearest_points = self.find_nearest_latlon("./foo.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            eccodes_lons.append(eccodes_lon)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol
        assert len(eccodes_lats) == 56
