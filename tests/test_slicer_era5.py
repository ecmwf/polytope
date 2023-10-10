import os

import numpy as np
import requests
from earthkit import data

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingEra5Data:
    # This test requires an internet connection

    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/era5-levels-members.grib"

        local_directory = "./tests/data"

        if not os.path.exists(local_directory):
            os.makedirs(local_directory)

        # Construct the full path for the local file
        local_file_path = os.path.join(local_directory, "era5-levels-members.grib")

        if not os.path.exists(local_file_path):
            session = requests.Session()
            response = session.get(nexus_url)
            if response.status_code == 200:
                # Save the downloaded data to the local file
                with open(local_file_path, "wb") as f:
                    f.write(response.content)

        ds = data.from_source("file", "./tests/data/era5-levels-members.grib")
        array = ds.to_xarray().isel(step=0).t
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        options = {"lat": {"transformation": {"reverse": {True}}}}
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    def test_2D_box(self):
        request = Request(
            Box(["number", "isobaricInhPa"], [3, 0.0], [6, 1000.0]),
            Select("time", ["2017-01-02T12:00:00"]),
            Box(["latitude", "longitude"], lower_corner=[0.0, 0.0], upper_corner=[10.0, 30.0]),
            Select("step", [np.timedelta64(0, "s")]),
        )

        result = self.API.retrieve(request)
        # result.pprint()

        assert len(result.leaves) == 4 * 1 * 2 * 4 * 11
