import numpy as np
import pytest

from polytope_feature import ConvexPolytope
from polytope_feature.utility.combinatorics import group, tensor_product, validate_axes
from polytope_feature.utility.exceptions import (
    AxisNotFoundError,
    AxisOverdefinedError,
    AxisUnderdefinedError,
)


class TestCombinatorics:
    def setup_method(self, method):
        pass

    def test_group_and_product(self):
        p1 = ConvexPolytope(["x", "y"], [[1, 2], [3, 4], [5, 6]])
        p2 = ConvexPolytope(["a", "b"], [[1, 2], [3, 4], [5, 6]])
        p3 = ConvexPolytope(["b", "a"], [[1, 2], [3, 4], [5, 6]])
        p4 = ConvexPolytope(np.array(["a", "b"]), [[1, 2], [3, 4], [5, 6]])
        p5 = ConvexPolytope(("a", "b"), [[1, 2], [3, 4], [5, 6]])

        groups, all_axes = group([p1, p2, p3, p4, p5])

        assert len(groups) == 2
        assert len(groups[("x", "y")]) == 1
        assert len(groups[("a", "b")]) == 4
        assert len(all_axes) == 4

        combinations = tensor_product(groups)

        assert len(combinations) == 4
        for c in combinations:
            assert len(c) == 2

    def test_group_with_different_number_of_axes(self):
        p1 = ConvexPolytope(["x", "y"], [[1, 2], [3, 4], [5, 6]])
        p2 = ConvexPolytope(["a", "b", "c"], [[1, 2], [3, 4], [5, 6]])

        groups, all_axes = group([p1, p2])

        assert len(groups) == 2
        assert len(groups[("x", "y")]) == 1
        assert len(groups[("a", "b", "c")]) == 1
        assert len(all_axes) == 5

    def test_validate_axes(self):
        with pytest.raises(AxisNotFoundError):
            validate_axes(["x", "y", "z"], ["x", "y", "z", "a"])
        with pytest.raises(AxisUnderdefinedError):
            validate_axes(["x", "y", "z"], ["x", "y"])
        with pytest.raises(AxisUnderdefinedError):
            validate_axes(["x", "y", "z"], ["x", "y", "b"])
        with pytest.raises(AxisUnderdefinedError):
            validate_axes(["x", "y", "z"], [])
        with pytest.raises(AxisUnderdefinedError):
            validate_axes(["x", "y", "z"], ["a"])
        with pytest.raises(AxisOverdefinedError):
            validate_axes(["x", "y", "z"], ["x", "x", "y", "z"])
        with pytest.raises(AxisOverdefinedError):
            validate_axes(["x", "y", "z"], ["x", "x", "x"])

        assert validate_axes([], [])
        assert validate_axes(["x"], ["x"])
        assert validate_axes(["x", "y", "z"], ["x", "y", "z"])
        assert validate_axes(["x", "y", "z"], ["z", "x", "y"])


TestCombinatorics().test_group_and_product()
TestCombinatorics().test_validate_axes()
