from types import SimpleNamespace

import numpy as np
import pandas as pd
import xarray as xr

from polytope_feature.datacube.backends.fdb import FDBDatacube
from polytope_feature.datacube.datacube_axis import UnsliceableDatacubeAxis
from polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change import (
    DatacubeAxisTypeChange,
    TypeChangeStrToFloat,
    TypeChangeSubHourlyTimeSteps,
    TypeChangeSubHourlyTimeStepsCompact,
)
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
            "axis_config": [
                {
                    "axis_name": "step",
                    "transformations": [{"name": "type_change", "type": "int"}],
                }
            ],
            "compressed_axes_config": ["step"],
        }
        self.API = Polytope(datacube=array, options=options)

    def test_int_type_change_axis(self):
        request = Request(Select("step", [0]))
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].flatten()["step"] == (0,)

    def test_float_type_change_axis(self):
        type_change_transform = TypeChangeStrToFloat("step", "float")

        assert type_change_transform.transform_type("0.5") == 0.5
        assert type_change_transform.transform_type("0") == 0.0

        assert type_change_transform.make_str([0.1]) == ("0.1",)
        assert type_change_transform.make_str([0.0]) == ("0",)

    def test_subhourly_step_type_change_axis(self):
        type_change_transform = TypeChangeSubHourlyTimeSteps("step", "subhourly_step")

        assert type_change_transform.transform_type("2") == pd.Timedelta(hours=2)
        assert type_change_transform.transform_type("15") == pd.Timedelta(hours=15)
        assert type_change_transform.transform_type("15h") == pd.Timedelta(hours=15)
        assert type_change_transform.transform_type(3) == pd.Timedelta(hours=3)
        assert type_change_transform.transform_type("45m") == pd.Timedelta(minutes=45)
        assert type_change_transform.transform_type("1h30m") == pd.Timedelta(hours=1, minutes=30)
        assert type_change_transform.transform_type("70m") == pd.Timedelta(hours=1, minutes=10)
        assert type_change_transform.transform_type("1h15m") == pd.Timedelta(hours=1, minutes=15)
        assert type_change_transform.transform_type("26h30m15s") == pd.Timedelta(hours=26, minutes=30, seconds=15)

        assert type_change_transform.make_str([pd.Timedelta(hours=1, minutes=15)]) == ["1h15m"]
        assert type_change_transform.make_str([pd.Timedelta(minutes=20)]) == ["20m"]
        assert type_change_transform.make_str([pd.Timedelta(hours=2)]) == ["2"]
        assert type_change_transform.make_str([pd.Timedelta(hours=0)]) == ["0"]
        assert type_change_transform.make_str([pd.Timedelta(seconds=30)]) == ["30s"]
        assert type_change_transform.make_str([pd.Timedelta(days=1)]) == ["24"]
        assert type_change_transform.make_str([pd.Timedelta(days=1, hours=2, minutes=20)]) == ["26h20m"]

    def test_subhourly_step_type_change_preserves_step_ranges(self):
        type_change_transform = TypeChangeSubHourlyTimeSteps("step", "subhourly_step")

        assert type_change_transform.transform_type("11h45m-15h45m") == "11h45m-15h45m"
        assert type_change_transform.transform_type("0-45m") == "0-45m"
        assert type_change_transform.make_str(["0-45m"]) == ["0-45m"]

    def test_subhourly_step_type_change_sorts_preserved_ranges_after_timedeltas(self):
        type_change_transform = DatacubeAxisTypeChange("step", SimpleNamespace(type="subhourly_step"))

        values = [
            pd.Timedelta(hours=15, minutes=45),
            "11h45m-15h45m",
            pd.Timedelta(hours=11, minutes=45),
        ]

        assert type_change_transform.change_val_type("step", values) == [
            pd.Timedelta(hours=11, minutes=45),
            pd.Timedelta(hours=15, minutes=45),
            "11h45m-15h45m",
        ]

    def test_subhourly_step_request_tree_preserves_hyphenated_labels(self):
        axis_options = [
            SimpleNamespace(
                axis_name="step",
                transformations=[SimpleNamespace(name="type_change", type="subhourly_step")],
            )
        ]
        datacube = FDBDatacube(
            gj=SimpleNamespace(),
            axis_options=axis_options,
            alternative_axes=[SimpleNamespace(axis_name="step", values=["0-15", "14-15", "0-1h30m", "15", "15h"])],
        )
        datacube._axes.pop("values")
        datacube.complete_axes.remove("values")
        seed_array = xr.DataArray(np.random.randn(1), dims=("seed",), coords={"seed": [0]})
        api = Polytope(datacube=seed_array, options={})
        api.datacube = datacube
        api.engine_options = {"step": "hullslicer"}
        api.engines = api.create_engines()

        for requested_value in ["0-15", "14-15", "0-1h30m"]:
            request_tree = api.slice(datacube, Request(Select("step", [requested_value])).polytopes())
            step_node = request_tree.children[0]

            assert step_node.values == (requested_value,)

    def test_subhourly_step_request_tree_keeps_distinct_hyphenated_labels(self):
        axis_options = [
            SimpleNamespace(
                axis_name="step",
                transformations=[SimpleNamespace(name="type_change", type="subhourly_step")],
            )
        ]
        datacube = FDBDatacube(
            gj=SimpleNamespace(),
            axis_options=axis_options,
            alternative_axes=[SimpleNamespace(axis_name="step", values=["0-15", "14-15", "15"])],
        )
        datacube._axes.pop("values")
        datacube.complete_axes.remove("values")
        seed_array = xr.DataArray(np.random.randn(1), dims=("seed",), coords={"seed": [0]})
        api = Polytope(datacube=seed_array, options={})
        api.datacube = datacube
        api.engine_options = {"step": "hullslicer"}
        api.engines = api.create_engines()

        request_tree = api.slice(datacube, Request(Select("step", ["0-15", "14-15"])).polytopes())

        assert [child.values for child in request_tree.children] == [("0-15", "14-15")]

    def test_subhourly_step_request_tree_supports_mixed_labels_and_timedeltas(self):
        axis_options = [
            SimpleNamespace(
                axis_name="step",
                transformations=[SimpleNamespace(name="type_change", type="subhourly_step")],
            )
        ]
        datacube = FDBDatacube(
            gj=SimpleNamespace(),
            axis_options=axis_options,
            alternative_axes=[SimpleNamespace(axis_name="step", values=["0-15", "14-15", "15"])],
        )
        datacube._axes.pop("values")
        datacube.complete_axes.remove("values")
        seed_array = xr.DataArray(np.random.randn(1), dims=("seed",), coords={"seed": [0]})
        api = Polytope(datacube=seed_array, options={})
        api.datacube = datacube
        api.engine_options = {"step": "hullslicer"}
        api.engines = api.create_engines()

        request_tree = api.slice(datacube, Request(Select("step", ["0-15", "15"])).polytopes())

        assert [child.values for child in request_tree.children] == [(pd.Timedelta(hours=15), "0-15")]

    def test_find_standard_indices_between_mixed_duplicates_with_surrounding(self):
        axis = UnsliceableDatacubeAxis()
        axis.name = "step"
        indexes = [pd.Timedelta(hours=0), "11h45m-15h45m", "11h45m-15h45m", "11h45m-15h45m", "next"]

        assert axis.find_standard_indices_between(indexes, "11h45m-15h45m", "11h45m-15h45m", None, "surrounding") == [
            pd.Timedelta(hours=0),
            "11h45m-15h45m",
            "11h45m-15h45m",
            "11h45m-15h45m",
            "next",
        ]

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
