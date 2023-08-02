from polytope.datacube.FDB_datacube import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        grid_options = {
            "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}}
        }
        config = {"class": "od", "expver": "0001", "levtype": "sfc", "step": 11}
        self.xarraydatacube = FDBDatacube(config, axis_options=grid_options)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=self.xarraydatacube, engine=self.slicer)

    # Testing different shapes

    def test_2D_box(self):
        request = Request(
            Select("step", [11]),
            Select("levtype", ["sfc"]),
            Select("date", ["20230710T120000"]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", [151130]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 9
