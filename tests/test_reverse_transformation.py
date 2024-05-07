import numpy as np
import xarray as xr

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select


class TestSlicingReverseTransformation:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(4),
            dims=("lat"),
            coords={
                "lat": [4, 3, 2, 1],
            },
        )
        options = {"config": [{"axis_name": "lat", "transformations": [{"name": "reverse", "is_reverse": True}]}]}
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    def test_reverse_transformation(self):
        request = Request(Select("lat", [1, 2, 3]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
