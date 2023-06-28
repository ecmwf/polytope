import numpy as np
import xarray as xr

from polytope.datacube.datacube_request_tree import IndexTree
from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope
from polytope.shapes import Box


class TestSlicerComponents:
    def setup_method(self, method):
        array = xr.DataArray(
            np.random.randn(4, 100),
            dims=("step", "level"),
            coords={
                "step": np.arange(3, 15, 3),
                "level": np.arange(0, 100, 1),
            },
        )
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_extract(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        assert request.axis == IndexTree.root
        assert request.parent is None
        assert request.value is None
        assert len(request.leaves) == 6
        assert request.leaves[0].axis.name == "level"
        assert len(request.children) == 2
        assert request.children[0].axis.name == "step"
        assert request.children[0].value == 3.0
        assert request.children[1].value == 6.0
        for i in range(len(request.leaves)):
            assert request.leaves[i].value in [1.0, 2.0, 3.0]
