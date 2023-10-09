import os

import requests
from earthkit import data

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingMultipleTransformationsOneAxis:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"

        local_directory = "./tests/data"

        if not os.path.exists(local_directory):
            os.makedirs(local_directory)

        # Construct the full path for the local file
        local_file_path = os.path.join(local_directory, "foo.grib")

        if not os.path.exists(local_file_path):
            session = requests.Session()
            response = session.get(nexus_url)
            if response.status_code == 200:
                # Save the downloaded data to the local file
                with open(local_file_path, "wb") as f:
                    f.write(response.content)

        ds = data.from_source("file", "./tests/data/foo.grib")
        self.latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        self.latlon_array = self.latlon_array.t2m
        self.xarraydatacube = XArrayDatacube(self.latlon_array)
        self.options = {
            "values": {
                "transformation": {
                    "mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                }
            },
            "longitude": {"transformation": {"cyclic": [0, 360.0]}},
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.latlon_array, engine=self.slicer, axis_options=self.options)

    def test_merge_axis(self):
        request = Request(
            Select("number", [0]),
            Select("time", ["2023-06-25T12:00:00"]),
            Select("step", ["00:00:00"]),
            Select("surface", [0]),
            Select("valid_time", ["2023-06-25T12:00:00"]),
            Box(["latitude", "longitude"], [0, 359.8], [0.2, 361.2]),
        )
        result = self.API.retrieve(request)
        # result.pprint()
        assert result.leaves[-1].flatten()["longitude"] == 360.0
        assert result.leaves[0].flatten()["longitude"] == 0.070093457944
