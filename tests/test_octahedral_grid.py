import pytest
import yaml
from earthkit import data
from helper_functions import download_test_data, find_nearest_latlon

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestOctahedralGrid:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
        download_test_data(nexus_url, "foo.grib")

        ds = data.from_source("file", "./tests/data/foo.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        self.latlon_array = self.latlon_array.t2m
        self.xarraydatacube = XArrayDatacube(self.latlon_array)
        self.options = yaml.safe_load(
                                    """
                            config:
                                - axis_name: values
                                  transformations:
                                    - name: "mapper"
                                      type: "octahedral"
                                      resolution: 1280
                                      axes: ["latitude", "longitude"]
                            """
        )
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.latlon_array, engine=self.slicer, axis_options=self.options)

    @pytest.mark.internet
    def test_octahedral_grid(self):
        request = Request(
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
            Select("number", [0]),
            Select("time", ["2023-06-25T12:00:00"]),
            Select("step", ["00:00:00"]),
            Select("surface", [0]),
            Select("valid_time", ["2023-06-25T12:00:00"]),
        )
        result = self.API.retrieve(request)
        assert len(result.leaves) == 9

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
            nearest_points = find_nearest_latlon("./tests/data/foo.grib", lat, lon)
            eccodes_lat = nearest_points[0][0]["lat"]
            eccodes_lon = nearest_points[0][0]["lon"]
            eccodes_lats.append(eccodes_lat)
            assert eccodes_lat - tol <= lat
            assert lat <= eccodes_lat + tol
            assert eccodes_lon - tol <= lon
            assert lon <= eccodes_lon + tol
        assert len(eccodes_lats) == 9
