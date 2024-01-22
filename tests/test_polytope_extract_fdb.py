import pandas as pd

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select


class TestPolytopeExtract:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.slicer = HullSlicer()
        self.engine_options = {
            "step": "hullslicer",
            "levtype": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
            "class": "hullslicer",
            "date": "hullslicer",
            "type": "hullslicer",
            "stream": "hullslicer",
            "param": "hullslicer",
            "expver": "hullslicer",
            "domain": "hullslicer",
        }
        quadtree_points = [[10, 10], [0.035149384216, 0.0], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        self.options = {
            "values": {"mapper": {"type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}},
            "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
            "step": {"type_change": "int"},
            "number": {"type_change": "int"},
        }
        self.config = {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"}
        self.fdbdatacube = FDBDatacube(self.config, axis_options=self.options, point_cloud_options=quadtree_points)
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            axis_options=self.options,
            engine_options=self.engine_options,
            point_cloud_options=quadtree_points,
        )

    # Testing different shapes

    def test_2D_box(self):
        # request = Request(Box(["step", "level"], [3, 10], [6, 11]), Box(["latitude", "longitude"], [0, 0], [20, 20]))
        request = Request(
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230625T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
            # TODO: why if we set the min_longitude= -0.1 does this not give back the points at lon=0?
            Box(["latitude", "longitude"], [0, -0.001], [10, 10]),
        )
        result = self.API.retrieve(request)

        result.pprint()
        assert len(result.leaves) == 3
