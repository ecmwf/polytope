import numpy as np
import xarray as xr

from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.datacube.tensor_index_tree import TensorIndexTree
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope
from polytope_feature.shapes import Box


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
        options = {"compressed_axes_config": ["level", "step"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_extract(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        assert request.axis == TensorIndexTree.root
        assert request.parent is None
        assert request.values is tuple()
        request.pprint()
        assert len(request.leaves) == 2
        assert request.leaves[0].axis.name == "level"
        assert len(request.children) == 2
        assert request.children[0].axis.name == "step"
        assert request.children[0].values == (3.0,)
        assert request.children[1].values == (6.0,)
        for i in range(len(request.leaves)):
            assert request.leaves[i].values == (
                1.0,
                2.0,
                3.0,
            )
