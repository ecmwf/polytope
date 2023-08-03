import numpy as np
import xarray as xr

from polytope.datacube.datacube_axis import (
    DatacubeAxis,
    FloatDatacubeAxis,
    FloatDatacubeAxisCyclic,
    IntDatacubeAxis,
    IntDatacubeAxisCyclic,
)
from polytope.datacube.backends.xarray import XArrayDatacube


class TestCreateAxis:
    def test_create_axis(self):
        array = xr.DataArray(
            np.random.randn(3, 6, 129),
            dims=("date", "step", "long"),
            coords={
                "date": [0.1, 0.2, 0.3],
                "step": [0, 3, 6, 9, 12, 15],
                "long": range(1, 130),
            },
        )
        options = {"Cyclic": [1, 10]}
        datacube = XArrayDatacube(array, options)
        DatacubeAxis.create_axis(options, "long", array["long"], datacube)
        assert type(datacube._axes["long"]) == IntDatacubeAxisCyclic
        options = {}
        DatacubeAxis.create_axis(options, "step", array["step"], datacube)
        assert type(datacube._axes["step"]) == IntDatacubeAxis
        grid_options = {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}}
        DatacubeAxis.create_axis(grid_options, "date", array["date"], datacube)
        assert type(datacube._axes["latitude"]) == FloatDatacubeAxis
        assert type(datacube._axes["longitude"]) == FloatDatacubeAxis

    def test_create_cyclic_and_mapper(self):
        array = xr.DataArray(
            np.random.randn(3, 6, 129),
            dims=("date", "step", "long"),
            coords={
                "date": [0.1, 0.2, 0.3],
                "step": [0, 3, 6, 9, 12, 15],
                "long": range(1, 130),
            },
        )
        options = {
            "date": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "latitude": {"Cyclic": [1, 10]},
        }
        datacube = XArrayDatacube(array, options)
        grid_options = {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}}
        DatacubeAxis.create_axis(grid_options, "date", array["date"], datacube)
        assert type(datacube._axes["latitude"]) == FloatDatacubeAxisCyclic
        assert datacube._axes.get("date", {}) == {}
