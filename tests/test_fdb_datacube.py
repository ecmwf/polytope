from polytope.datacube.FDB_datacube import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        grid_options = {"values": {"grid_map": {"type": ["octahedral", 1280], "axes": ["latitude", "longitude"]}}}
        config = {"class" : "od",
                  "expver" : "0001",
                  "levtype" : "pl",
                  "step" : 4}
        self.xarraydatacube = FDBDatacube(config, options={}, grid_options=grid_options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.xarraydatacube, engine=self.slicer)

    # Testing different shapes

    def test_2D_box(self):
        request = Request(Box(["step", "level"], [3, 10], [6, 11]),
                          Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 36
