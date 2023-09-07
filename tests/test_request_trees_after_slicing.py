import numpy as np
import xarray as xr

from polytope.datacube.backends.xarray import XArrayDatacube
from polytope.datacube.datacube_axis import IntDatacubeAxis
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope
from polytope.shapes import Box


class TestIndexTreesAfterSlicing:
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

    def test_path_values(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        datacube_path = request.leaves[0].flatten()
        # request.pprint()
        assert datacube_path.values() == tuple([3.0, 1.0])
        assert len(datacube_path.values()) == 2

    def test_path_keys(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        datacube_path = request.leaves[0].flatten()
        assert datacube_path.keys()[0] == "step"
        assert datacube_path.keys()[1] == "level"

    def test_path_pprint(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        datacube_path = request.leaves[0].flatten()
        datacube_path.pprint()

    def test_flatten(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        path = request.leaves[0].flatten()
        assert path["step"] == 3.0
        assert path["level"] == 1.0

    def test_add_child(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        request1 = request.leaves[0]
        request2 = request.leaves[0]
        # Test adding child
        axis1 = IntDatacubeAxis()
        axis1.name = "lat"
        request2.create_child(axis1, 4.1)
        assert request2.leaves[0].axis.name == "lat"
        assert request2.leaves[0].value == 4.1
        axis2 = IntDatacubeAxis()
        axis2.name = "level"
        # Test getting child
        assert request1.create_child(axis2, 3.0).axis.name == "level"
        assert request1.create_child(axis2, 3.0).value == 3.0

    def test_pprint(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        request.pprint()

    def test_remove_branch(self):
        box = Box(["step", "level"], [3.0, 1.0], [6.0, 3.0])
        polytope = box.polytope()
        request = self.slicer.extract(self.xarraydatacube, polytope)
        prev_request_size = len(request.leaves)
        request.leaves[0].remove_branch()
        new_request_size = len(request.leaves)
        assert prev_request_size == new_request_size + 1
        axis1 = IntDatacubeAxis()
        axis2 = IntDatacubeAxis()
        axis1.name = "step"
        axis2.name = "level"
        # Test if remove_branch() also removes longer branches
        request1 = request.create_child(axis1, 1.0)
        request2 = request1.create_child(axis2, 0.0)
        request2.remove_branch()
        assert request1.is_root()  # removed from original
