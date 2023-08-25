from earthkit import data

from polytope.datacube.backends.datacube import Datacube
from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.datacube.datacube_axis import FloatDatacubeAxis
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope


class TestOctahedralGrid:
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
            }
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=latlon_array, engine=self.slicer, axis_options=grid_options)
        self.datacube = self.API.datacube

    def test_created_axes(self):
        assert self.datacube._axes["latitude"].has_mapper
        assert self.datacube._axes["longitude"].has_mapper
        assert type(self.datacube._axes["longitude"]) == FloatDatacubeAxis
        assert not ("values" in self.datacube._axes.keys())
        assert self.datacube._axes["latitude"].remap([0], {})[0][:5] == [89.94618771566562, 89.87647835333229,
                                                                         89.80635731954224, 89.73614327160958,
                                                                         89.6658939412157]
        assert self.datacube._axes["longitude"].remap([0], {"latitude": 89.94618771566562})[0][:8] == [0.0, 18.0, 36.0,
                                                                                                       54.0, 72.0, 90.0,
                                                                                                       108.0, 126.0]
        assert len(self.datacube._axes["longitude"].remap([0], {"latitude": 89.94618771566562})[0]) == 20
        lon_ax = self.datacube._axes["longitude"]
        lat_ax = self.datacube._axes["latitude"]
        (path, unmapped_path) = lat_ax.unmap_to_datacube({"latitude": 89.94618771566562}, {})
        assert path == {}
        assert unmapped_path == {'latitude': 89.94618771566562}
        (path, unmapped_path) = lon_ax.unmap_to_datacube({"longitude": 0.0}, {"latitude": 89.94618771566562})
        assert path == {}
        assert unmapped_path == {"values": 0}
        assert lat_ax.find_indices_between(lat_ax, [[89.94618771566562, 89.87647835333229]],
                                           89.87, 90, self.datacube) == [[89.94618771566562, 89.87647835333229]]
