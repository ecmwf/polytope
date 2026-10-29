"""The vectorised regular / local_regular ``unmap`` gives exactly the grid indices of the original per-point code."""

import numpy as np
import pytest

from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.local_regular import (
    LocalRegularGridMapper,
)
from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.regular import (
    RegularGridMapper,
)


def reference_regular_unmap(mapper, first_val, second_vals):
    """``RegularGridMapper.unmap`` before it was vectorised (one scan of the full longitude list per point)."""
    tol = 1e-8
    first_val = [i for i in mapper._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
    first_idx = mapper._first_axis_vals.index(first_val)
    return_idxs = []
    for second_val in second_vals:
        second_val = [i for i in mapper.second_axis_vals(first_val) if second_val - tol <= i <= second_val + tol][0]
        second_idx = mapper.second_axis_vals(first_val).index(second_val)
        return_idxs.append(mapper.axes_idx_to_regular_idx(first_idx, second_idx))
    return return_idxs


def reference_local_regular_unmap(mapper, first_val, second_vals):
    """``LocalRegularGridMapper.unmap`` before its nearest-neighbour step was vectorised."""
    first_array = mapper._first_axis_vals
    second_array = mapper._second_axis_vals
    second_vals = np.asarray(second_vals)
    if mapper._axis_reversed[mapper._mapped_axes[0]]:
        first_idx = np.searchsorted(-first_array, -first_val[0])
    else:
        first_idx = np.searchsorted(first_array, first_val[0])
    if first_idx > 0 and first_idx < len(first_array):
        left_val = first_array[first_idx - 1]
        right_val = first_array[first_idx]
        if abs(first_val[0] - left_val) < abs(first_val[0] - right_val):
            first_idx -= 1
    second_idxs = np.searchsorted(second_array, second_vals)
    for i, second_idx in enumerate(second_idxs):
        if second_idx > 0 and second_idx < len(second_array):
            left_val = second_array[second_idx - 1]
            right_val = second_array[second_idx]
            if abs(second_vals[i] - left_val) < abs(second_vals[i] - right_val):
                second_idxs[i] -= 1
    return first_idx * (mapper.second_resolution + 1) + second_idxs


def regular(resolution, lat_reversed=True):
    return RegularGridMapper(
        "values", ["latitude", "longitude"], resolution, axis_reversed={"latitude": lat_reversed, "longitude": False}
    )


@pytest.mark.parametrize("resolution", [1, 30, 90, 360, 1280])
@pytest.mark.parametrize("lat_reversed", [True, False])
def test_regular_unmap_matches_reference(resolution, lat_reversed):
    mapper = regular(resolution, lat_reversed)
    rng = np.random.default_rng(resolution)
    lats = mapper._first_axis_vals
    lons = mapper.second_axis_vals(None)
    for row in rng.choice(len(lats), size=min(len(lats), 6), replace=False).tolist() + [0, len(lats) - 1]:
        k = rng.choice(len(lons), size=min(len(lons), 200), replace=False)
        # grid values, values jittered within the tolerance, the first/last points of the line
        second = np.concatenate(
            [
                np.asarray(lons)[k],
                np.asarray(lons)[k[:50]] + rng.uniform(-9e-9, 9e-9, size=len(k[:50])),
                [lons[0], lons[-1], lons[0] + 5e-9, lons[-1] - 5e-9],
            ]
        )
        first = [lats[row] + rng.uniform(-9e-9, 9e-9)]
        got = mapper.unmap(first, second)
        assert got == reference_regular_unmap(mapper, first, second)
        assert all(type(i) is int for i in got)
        # tuples and numpy leaf arrays alike
        from_tuple = mapper.unmap((lats[row],), tuple(np.asarray(lons)[k].tolist()))
        assert from_tuple == reference_regular_unmap(mapper, (lats[row],), np.asarray(lons)[k])


@pytest.mark.parametrize(
    "first, second",
    [
        ([0.5e-3], [0.0]),  # latitude between grid lines
        ([0.0], [1e-4]),  # longitude between grid points
        ([0.0], [-1.0]),  # before the first point
        ([0.0], [360.0]),  # past the last point (360 is not on the grid)
        ([0.0], [0.0, 3.0, np.nan]),
    ],
)
def test_regular_unmap_rejects_values_off_the_grid(first, second):
    mapper = regular(30)
    with pytest.raises(IndexError):
        reference_regular_unmap(mapper, first, second)
    with pytest.raises(IndexError):
        mapper.unmap(first, second)


def test_regular_unmap_of_no_points():
    mapper = regular(30)
    assert mapper.unmap([0.0], []) == [] == reference_regular_unmap(mapper, [0.0], [])
    assert mapper.unmap([0.0], np.empty(0)) == []


EFAS_LOCAL = [22.758333333333333, 72.24166666666666, -25.241666666666667, 50.24166666666667]


@pytest.mark.parametrize(
    "resolution, local, axis_reversed",
    [
        ([2969, 4529], EFAS_LOCAL, {"latitude": True, "longitude": False}),
        (80, [-40, 40, -20, 60], {"latitude": False, "longitude": False}),
    ],
)
def test_local_regular_unmap_matches_reference(resolution, local, axis_reversed):
    mapper = LocalRegularGridMapper("values", ["latitude", "longitude"], resolution, None, local, axis_reversed)
    rng = np.random.default_rng(7)
    lats = mapper._first_axis_vals
    lons = mapper._second_axis_vals
    for _ in range(20):
        first = [float(rng.choice(lats)) + rng.uniform(-1e-9, 1e-9)]
        # grid points, arbitrary points (nearest-neighbour lookup) and points outside the area
        second = np.concatenate(
            [
                rng.choice(lons, size=500),
                rng.uniform(lons[0] - 1, lons[-1] + 1, size=500),
                [lons[0], lons[-1], (lons[0] + lons[1]) / 2],
            ]
        )
        got = mapper.unmap(first, second)
        expected = reference_local_regular_unmap(mapper, first, second)
        assert isinstance(got, np.ndarray)
        np.testing.assert_array_equal(got, expected)
    assert len(mapper.unmap([lats[3]], [])) == 0
