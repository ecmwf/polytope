import numpy as np
import xarray as xr

from polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change import (
    TypeChangeStrToFloat,
)
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Select


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
        options = {
            "axis_config": [{"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]}],
            "compressed_axes_config": ["step"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_merge_axis(self):
        request = Request(Select("step", [0]))
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].flatten()["step"] == (0,)

    def test_subhourly_step_type_change_axis(self):
        type_change_transform = TypeChangeStrToFloat("step", "float")

        assert type_change_transform.transform_type("0.5") == 0.5
        assert type_change_transform.transform_type("0") == 0.0

        assert type_change_transform.make_str([0.1]) == "0.1"
        assert type_change_transform.make_str([0.0]) == "0"
