import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change import (
    TypeChangeSubHourlyTimeSteps,
    TypeChangeSubHourlyTimeStepsCompact,
)
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Select


class TestIntTypeChangeTransformation:
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

    def test_int_type_change_axis(self):
        request = Request(Select("step", [0]))
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].flatten()["step"] == (0,)

    def test_subhourly_step_type_change_axis(self):
        type_change_transform = TypeChangeSubHourlyTimeSteps("step", "subhourly_step")

        assert type_change_transform.transform_type("2") == pd.Timedelta(hours=2)
        assert type_change_transform.transform_type(3) == pd.Timedelta(hours=3)
        assert type_change_transform.transform_type("70m") == pd.Timedelta(hours=1, minutes=10)
        assert type_change_transform.transform_type("1h15m") == pd.Timedelta(hours=1, minutes=15)

        assert type_change_transform.make_str([pd.Timedelta(hours=1, minutes=15)]) == "1h15m"
        assert type_change_transform.make_str([pd.Timedelta(minutes=20)]) == "20m"
        assert type_change_transform.make_str([pd.Timedelta(hours=2)]) == "2"
        assert type_change_transform.make_str([pd.Timedelta(hours=0)]) == "0"

    def test_subhourly_step_compact_type_change_axis(self):
        type_change_transform = TypeChangeSubHourlyTimeStepsCompact("step", "subhourly_step_compact")

        assert type_change_transform.transform_type("2") == pd.Timedelta(hours=2)
        assert type_change_transform.transform_type(3) == pd.Timedelta(hours=3)
        assert type_change_transform.transform_type("70m") == pd.Timedelta(hours=1, minutes=10)
        assert type_change_transform.transform_type("1h15m") == pd.Timedelta(hours=1, minutes=15)

        assert type_change_transform.make_str([pd.Timedelta(hours=1, minutes=15)]) == "75m"
        assert type_change_transform.make_str([pd.Timedelta(minutes=20)]) == "20m"
        assert type_change_transform.make_str([pd.Timedelta(hours=2)]) == "2"
        assert type_change_transform.make_str([pd.Timedelta(hours=0)]) == "0"
