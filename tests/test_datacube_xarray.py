import datetime

import numpy as np
import pandas as pd
import pytest
import xarray as xr

from polytope_feature.datacube import Datacube, DatacubePath
from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.datacube.datacube_axis import (
    FloatDatacubeAxis,
    IntDatacubeAxis,
    PandasTimestampDatacubeAxis,
)
from polytope_feature.utility.exceptions import AxisNotFoundError, AxisOverdefinedError


class TestXarrayDatacube:
    def setup_method(self, method):
        pass

    def test_validate(self):
        dims = np.random.randn(1, 1, 1)
        array = xr.Dataset(data_vars=dict(param=(["x", "y", "z"], dims)), coords={"x": [1], "y": [1], "z": [1]})
        array = array.to_array()

        datacube = Datacube.create(array, axis_options={})

        datacube.validate(["x", "y", "z", "variable"])
        datacube.validate(["x", "z", "y", "variable"])

        with pytest.raises(AxisNotFoundError):
            datacube.validate(["x", "y", "z", "w", "variable"])

        with pytest.raises(AxisNotFoundError):
            datacube.validate(["w", "x", "y", "z", "variable"])

        with pytest.raises(AxisOverdefinedError):
            datacube.validate(["x", "x", "y", "z", "variable"])

    def test_create(self):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            np.random.randn(3, 6, 129),
            dims=("date", "step", "level"),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1, 130),
            },
        )

        for d, v in array.coords.variables.items():
            print(v.dtype)

        datacube = Datacube.create(array, axis_options={})

        # Check the factory created the correct type of datacube
        assert isinstance(datacube, XArrayDatacube)

        # Tests on "date" axis, path is empty so we look at the whole datacube
        partial_request = DatacubePath()

        # Check parsing a date correctly converts type to pd.Timestamp
        mapper = datacube.get_mapper("date")
        assert type(mapper.parse("2000-01-01")) == pd.Timestamp

        parsed = mapper.parse("2000-01-01")
        to_float = mapper.to_float(parsed)
        from_float = mapper.from_float(to_float)
        assert parsed == from_float

        # Check discretizing along 'date' axis with a range of dates
        label = PandasTimestampDatacubeAxis()
        label.name = "date"
        idxs = datacube.get_indices(partial_request, label, pd.Timestamp("2000-01-02"), pd.Timestamp("2000-03-31"))
        assert (idxs == pd.date_range(pd.Timestamp("2000-01-02"), pd.Timestamp("2000-01-03"), 2)).all()
        assert isinstance(idxs[0], pd.Timestamp)

        # Check discretizing along 'date' axis at a specific date gives one value
        label = PandasTimestampDatacubeAxis()
        label.name = "date"
        idxs = datacube.get_indices(partial_request, label, pd.Timestamp("2000-01-02"), pd.Timestamp("2000-01-02"))
        assert len(idxs) == 1
        assert isinstance(idxs[0], pd.Timestamp)
        assert idxs[0] == pd.Timestamp(pd.Timestamp("2000-01-02"))

        # Check discretizing along 'date' axis at a date which does not exist in discrete space gives no values
        label = PandasTimestampDatacubeAxis()
        label.name = "date"
        idxs = datacube.get_indices(
            partial_request, label, pd.Timestamp("2000-01-01-1200"), pd.Timestamp("2000-01-01-1200")
        )
        assert len(idxs) == 0

        # Tests on "step" axis, path is a sub-datacube at a specific date
        partial_request["date"] = (datetime.datetime.strptime("2000-01-01", "%Y-%m-%d"),)

        # Check parsing a step correctly converts type to int
        assert type(datacube.get_mapper("step").parse(3)) == float
        assert type(datacube.get_mapper("step").parse(3.0)) == float

        # Check discretizing along 'step' axis with a range of steps
        label = IntDatacubeAxis()
        label.name = "step"
        idxs = datacube.get_indices(partial_request, label, 0, 10)
        assert idxs == [0, 3, 6, 9]
        assert isinstance(idxs[0], int)

        partial_request["date"] = (datetime.datetime.strptime("2000-01-01", "%Y-%m-%d"),)

        # Check discretizing along 'step' axis at a specific step gives one value
        idxs = datacube.get_indices(partial_request, label, 3, 3)
        assert len(idxs) == 1
        assert idxs[0] == 3
        assert isinstance(idxs[0], int)

        partial_request["date"] = (datetime.datetime.strptime("2000-01-01", "%Y-%m-%d"),)

        # Check discretizing along 'step' axis at a step which does not exist in discrete space gives no values
        idxs = datacube.get_indices(partial_request, label, 4, 4)
        assert len(idxs) == 0

        # Tests on "level" axis, path is a sub-datacube at a specific date/step
        partial_request["date"] = (datetime.datetime.strptime("2000-01-01", "%Y-%m-%d"),)
        partial_request["step"] = (3,)

        # Check parsing a level correctly converts type to int
        assert type(datacube.get_mapper("level").parse(3)) == float
        assert type(datacube.get_mapper("level").parse(3.0)) == float

        # Check discretizing along 'level' axis with a range of levels
        label = FloatDatacubeAxis()
        label.name = "level"
        idxs = datacube.get_indices(partial_request, label, -0.3, 10)
        assert idxs == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        assert isinstance(idxs[0], int)
