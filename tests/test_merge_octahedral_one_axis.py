from earthkit import data

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicing4DXarrayDatacube:
    def setup_method(self, method):
        ds = data.from_source("file", "./tests/data/foo.grib")
        latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        latlon_array = latlon_array.t2m
        self.xarraydatacube = XArrayDatacube(latlon_array)
        grid_options = {
            "values": {
                "transformation": {
                    "mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                }
            },
            "longitude": {"transformation": {"cyclic": [0, 360.0]}},
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=latlon_array, engine=self.slicer, axis_options=grid_options)

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
        assert result.leaves[2].flatten()["longitude"] == 360.0
