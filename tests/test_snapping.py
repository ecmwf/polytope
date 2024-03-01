import numpy as np
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 3),
            dims=("level", "step"),
            coords={
                "level": [1, 3, 5],
                "step": [1, 3, 5],
            },
        )
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    # Testing different shapes

    def test_2D_point(self):
        request = Request(Select("level", [2], method="surrounding"), Select("step", [4], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 4
        for leaf in result.leaves:
            path = leaf.flatten()
            assert path["level"] in [1, 3]
            assert path["step"] in [3, 5]

    def test_2D_point_outside_datacube_left(self):
        request = Request(Select("level", [2], method="surrounding"), Select("step", [0], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 2
        for leaf in result.leaves:
            path = leaf.flatten()
            assert path["level"] in [1, 3]
            assert path["step"] == 1

    def test_2D_point_outside_datacube_right(self):
        request = Request(Select("level", [2], method="surrounding"), Select("step", [6], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 2
        for leaf in result.leaves:
            path = leaf.flatten()
            assert path["level"] in [1, 3]
            assert path["step"] == 5

    def test_1D_point_outside_datacube_right(self):
        request = Request(Select("level", [1]), Select("step", [6], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        for leaf in result.leaves:
            path = leaf.flatten()
            assert path["level"] == 1
            assert path["step"] == 5

    def test_1D_nonexisting_point(self):
        request = Request(Select("level", [2]), Select("step", [6], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.is_root()

    def test_1D_nonexisting_point_v2(self):
        request = Request(Select("level", [2], method="surrounding"), Select("step", [6]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.is_root()

    def test_1D_nonexisting_point_surrounding(self):
        request = Request(Select("level", [0], method="surrounding"), Select("step", [6], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        for leaf in result.leaves:
            path = leaf.flatten()
            assert path["level"] == 1
            assert path["step"] == 5
