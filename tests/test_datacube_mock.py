import pytest

from polytope_feature.datacube.backends.mock import MockDatacube
from polytope_feature.utility.exceptions import AxisNotFoundError, AxisOverdefinedError


class TestMockDatacube:
    def setup_method(self, method):
        pass

    def test_validate(self):
        datacube = MockDatacube({"x": 1, "y": 1, "z": 1})

        datacube.validate(["x", "y", "z"])
        datacube.validate(["x", "z", "y"])

        with pytest.raises(AxisNotFoundError):
            datacube.validate(["x", "y", "z", "w"])

        with pytest.raises(AxisNotFoundError):
            datacube.validate(["w", "x", "y", "z"])

        with pytest.raises(AxisOverdefinedError):
            datacube.validate(["x", "x", "y", "z"])
