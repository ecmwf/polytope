import pytest
from earthkit import data
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file
from helper_functions import download_test_data

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestOctahedralGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/healpix.grib"
        download_test_data(nexus_url, "healpix.grib")

        ds = data.from_source("file", "./tests/data/healpix.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(time=0).isel(isobaricInhPa=0).z
        self.xarraydatacube = XArrayDatacube(self.latlon_array)
        self.options = {
            "values": {
                "transformation": {"mapper": {"type": "healpix", "resolution": 32, "axes": ["latitude", "longitude"]}}
            },
            "longitude": {"transformation": {"cyclic": [0, 360]}},
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

    @pytest.mark.internet
    def test_healpix_grid(self):
        request = Request(
            Box(["latitude", "longitude"], [-2, -2], [10, 10]),
            Select("time", ["2022-12-14T12:00:00"]),
            Select("step", ["01:00:00"]),
            Select("isobaricInhPa", [500]),
            Select("valid_time", ["2022-12-14T13:00:00"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 40

        lats = []
        lons = []
        eccodes_lats = []
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
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol
        assert len(eccodes_lats) == 40
