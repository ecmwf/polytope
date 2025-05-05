import numpy as np
import xarray as xr

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box


class TestPolytopeExtract:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.array = xr.DataArray(
            np.random.randn(6, 129, 100),
            dims=("step", "level", "values"),
            coords={
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
                "values": range(0, 100),
            },
        )
        self.engine_options = {
            "step": "hullslicer",
            "level": "hullslicer",
            "latitude": "quadtree",
            "longitude": "quadtree",
        }
        self.quadtree_points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        self.options = {
            "axis_config": [
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "unstructured",
                            "resolution": 1280, "axes": ["latitude", "longitude"], "points": self.quadtree_points}
                    ],
                },
            ],
        }

    # Testing different shapes

    def test_2D_box(self):
        request = Request(Box(["step", "level"], [3, 10], [6, 11]), Box(["latitude", "longitude"], [0, 0], [20, 20]))
        self.API = Polytope(
            datacube=self.array,
            options=self.options,
            engine_options=self.engine_options,
            # point_cloud_options=self.quadtree_points,
        )
        result = self.API.retrieve(request)

        result.pprint()
        assert len(result.leaves) == 12
