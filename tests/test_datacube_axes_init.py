import earthkit.data as data
import pytest
from helper_functions import download_test_data

from polytope_feature.datacube.datacube_axis import FloatDatacubeAxis
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestInitDatacubeAxes:
    def setup_method(self, method):
        nexus_url = "https://get.ecmwf.int/test-data/polytope/test-data/foo.grib"
        download_test_data(nexus_url, "foo.grib")

        ds = data.from_source("file", "./tests/data/foo.grib")
        latlon_array = ds.to_xarray(engine="cfgrib").isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
        latlon_array = latlon_array.t2m
        self.options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
                    ],
                },
                {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
            ],
            "compressed_axes_config": [
                "longitude",
                "latitude",
                "levtype",
                "step",
                "date",
                "domain",
                "expver",
                "param",
                "class",
                "stream",
                "type",
            ],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=latlon_array,
            engine=self.slicer,
            options=self.options,
        )
        self.datacube = self.API.datacube

    @pytest.mark.internet
    def test_created_axes(self):
        assert self.datacube._axes["latitude"].has_mapper
        assert self.datacube._axes["longitude"].has_mapper
        assert isinstance(self.datacube._axes["longitude"], FloatDatacubeAxis)
        assert not ("values" in self.datacube._axes.keys())
        assert list(self.datacube._axes["latitude"].find_indexes({}, self.datacube)[:5]) == [
            89.94618771566562,
            89.87647835333229,
            89.80635731954224,
            89.73614327160958,
            89.6658939412157,
        ]
        assert self.datacube._axes["longitude"].find_indexes({"latitude": (89.94618771566562,)}, self.datacube)[:8] == [
            0.0,
            18.0,
            36.0,
            54.0,
            72.0,
            90.0,
            108.0,
            126.0,
        ]
        assert (
            len(self.datacube._axes["longitude"].find_indexes({"latitude": (89.94618771566562,)}, self.datacube)) == 20
        )
        assert self.datacube._axes["latitude"].find_indexes({}, self.datacube)[:5] == [
            89.94618771566562,
            89.87647835333229,
            89.80635731954224,
            89.73614327160958,
            89.6658939412157,
        ]
        assert self.datacube._axes["longitude"].find_indexes({"latitude": (89.94618771566562,)}, self.datacube)[:8] == [
            0.0,
            18.0,
            36.0,
            54.0,
            72.0,
            90.0,
            108.0,
            126.0,
        ]
        assert (
            len(self.datacube._axes["longitude"].find_indexes({"latitude": (89.94618771566562,)}, self.datacube)) == 20
        )
        lon_ax = self.datacube._axes["longitude"]
        lat_ax = self.datacube._axes["latitude"]
        (path_key, path, unmapped_path) = lat_ax.unmap_path_key({"latitude": 89.94618771566562}, {}, {})
        assert path == {}
        assert unmapped_path == {"latitude": 89.94618771566562}
        (path_key, path, unmapped_path) = lon_ax.unmap_path_key(
            {"longitude": (0.0,)}, {}, {"latitude": (89.94618771566562,)}
        )
        assert path == {}
        assert unmapped_path == {"latitude": (89.94618771566562,)}
        assert path_key == {"values": [0]}
        assert lat_ax.find_indices_between([89.94618771566562, 89.87647835333229], 89.87, 90, self.datacube, 0) == [
            89.94618771566562,
            89.87647835333229,
        ]

    @pytest.mark.internet
    def test_mapper_transformation_request(self):
        request = Request(
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
            Select("number", [0]),
            Select("time", ["2023-06-25T12:00:00"]),
            Select("step", ["00:00:00"]),
            Select("surface", [0]),
            Select("valid_time", ["2023-06-25T12:00:00"]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 3
