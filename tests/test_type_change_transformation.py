import numpy as np
import xarray as xr

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select


class TestTypeChangeTransformation:
    def setup_method(self, method):
        # Create a dataarray with 4 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(2),
            dims=("step"),
            coords={
                "step": ["0", "1"],
            },
        )
        self.array = array
        options = {"config": [{"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]}]}
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, axis_options=options)

    def test_merge_axis(self):
        request = Request(Select("step", [0]))
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].flatten()["step"] == (0,)
