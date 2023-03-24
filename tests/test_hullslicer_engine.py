import xarray as xr
import numpy as np
from decimal import *

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.shapes import *
from polytope.polytope import Polytope
from polytope.datacube.datacube_request_tree import DatacubeRequestTree

class TestSlicerComponents():

    def setup_method(self, method):

        array = xr.DataArray(
            np.random.randn(4,100),
            dims=("step","level"),
            coords={
                "step": np.arange(3, 15, 3),
                "level": np.arange(0,100,1),
            }
        )

        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_extract(self):
        box = Box(["step", "level"],[3.,1.],[6.,3.])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        assert request.axis == DatacubeRequestTree.root
        assert request.parent == None
        assert request.value == None
        assert len(request.leaves) == 6
        assert request.leaves[0].axis.name == "level"
        assert len(request.children) == 2
        assert request.children[0].axis.name == "step"
        assert request.children[0].value == 3.
        assert request.children[1].value == 6.
        for i in range(len(request.leaves)):
            # TODO: not sure in which order leaves are counted
            assert request.leaves[i].value in [1.,2.,3.]