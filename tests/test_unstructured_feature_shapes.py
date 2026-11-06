"""
Slices every shape polytope-mars builds on an unstructured grid, with levelist and step sliced before
latitude/longitude as in an ICON datacube.

Shapes that span latitude/longitude and also levelist or step (3D bounding box, 3D/4D trajectory) must
constrain those earlier axes too. If they only reach the slicer at the latitude axis, no level or step is
selected and the result is empty.

Each case is also sliced with polytope batching turned off, which must select exactly the same points.
"""

import numpy as np
import pytest
import xarray as xr

from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import (
    Box,
    Disk,
    Ellipsoid,
    Path,
    Point,
    Polygon,
    Select,
    Span,
    Union,
)

LATS, LONS = np.meshgrid(np.arange(46.0, 48.0, 0.05), np.arange(6.0, 9.5, 0.05), indexing="ij")
POINTS = list(zip(LATS.ravel().round(4), LONS.ravel().round(4)))
LEVELS = np.arange(70, 81)
STEPS = [0, 1, 2, 3]

LL = ["latitude", "longitude"]
LLL = LL + ["levelist"]
LLLS = LL + ["levelist", "step"]
A, B = [47.45, 8.55], [46.8, 6.9]
LEVEL_74, STEP_1 = Select("levelist", [74]), Select("step", [1])


def pairs(levels, steps):
    return {(level, step) for level in levels for step in steps}


# name: (shapes as built by polytope-mars plus Selects for the other keys, expected (level, step) pairs)
CASES = {
    "position": ([Point(LL, [A, B], method="nearest"), LEVEL_74, STEP_1], pairs([74], [1])),
    "timeseries": ([Point(LL, [A, B], method="nearest"), LEVEL_74, Span("step", 0, 3)], pairs([74], STEPS)),
    "vertical_profile": (
        [Union(LL, Point(LL, [A], method="nearest")), Span("levelist", 72, 75), STEP_1],
        pairs([72, 73, 74, 75], [1]),
    ),
    "bounding_box_2d": ([Union(LL, Box(LL, [46.8, 7.0], [47.0, 7.2])), LEVEL_74, STEP_1], pairs([74], [1])),
    "bounding_box_3d": ([Union(LLL, Box(LLL, [46.8, 7.0, 74], [47.0, 7.2, 76])), STEP_1], pairs([74, 75, 76], [1])),
    "union_of_3d_boxes": (
        [Union(LLL, Box(LLL, [46.8, 7.0, 74], [47.0, 7.2, 76]), Box(LLL, [47.3, 8.0, 78], [47.5, 8.2, 79])), STEP_1],
        pairs([74, 75, 76, 78, 79], [1]),
    ),
    "polygon": (
        [Union(LL, Polygon(LL, [[46.8, 7.0], [47.0, 7.0], [47.0, 7.3], [46.8, 7.0]])), LEVEL_74, STEP_1],
        pairs([74], [1]),
    ),
    "frame": (
        [Union(LL, Box(LL, [46.8, 7.0], [46.85, 7.3]), Box(LL, [46.95, 7.0], [47.0, 7.3])), LEVEL_74, STEP_1],
        pairs([74], [1]),
    ),
    "circle": ([Disk(LL, [47.0, 8.0], [0.1, 0.1]), LEVEL_74, STEP_1], pairs([74], [1])),
    "trajectory_2d_round": ([Path(LL, Disk(LL, [0, 0], [0.05, 0.05]), A, B), LEVEL_74, STEP_1], pairs([74], [1])),
    "trajectory_2d_box": ([Path(LL, Box(LL, [0, 0], [0.05, 0.05]), A, B), LEVEL_74, STEP_1], pairs([74], [1])),
    "trajectory_3d_round": (
        [Path(LLL, Ellipsoid(LLL, [0, 0, 0], [0.05] * 3), A + [74], B + [80]), STEP_1],
        pairs(range(74, 81), [1]),
    ),
    "trajectory_3d_box": (
        [Path(LLL, Box(LLL, [0, 0, 0], [0.05] * 3), A + [74], B + [80]), STEP_1],
        pairs(range(74, 81), [1]),
    ),
    # level and step change together along the path: step = (level - 74) / 2
    "trajectory_4d_box": (
        [Path(LLLS, Box(LLLS, [0] * 4, [0.05] * 4), A + [74, 0], B + [80, 3])],
        {(74, 0), (76, 1), (78, 2), (80, 3)},
    ),
}


def make_api():
    # levelist and step come before the unstructured values axis, so they are sliced before latitude.
    arr = xr.DataArray(
        np.zeros((len(LEVELS), len(STEPS), len(POINTS))),
        dims=["levelist", "step", "values"],
        coords={"levelist": LEVELS, "step": STEPS},
    )
    options = {
        "axis_config": [
            {
                "axis_name": "values",
                "transformations": [{"name": "mapper", "type": "unstructured", "axes": LL, "points": POINTS}],
            }
        ],
        "engine_options": {
            "latitude": "quadtree",
            "longitude": "quadtree",
            "levelist": "hullslicer",
            "step": "hullslicer",
        },
    }
    return Polytope(datacube=arr, options=options)


def selected_points(shapes):
    """Slice with a fresh Polytope and return the selected (level, step, latitude, longitude) tuples."""
    tree = make_api().retrieve(Request(*shapes))
    selected = set()
    for leaf in tree.leaves:
        if not hasattr(leaf, "coordinates"):
            continue
        path = {node.axis.name: node.values for node in leaf.get_ancestors()[:-1]}
        for level in path.get("levelist", (None,)):
            for step in path.get("step", (None,)):
                for lat, lon in leaf.coordinates:
                    selected.add((level, step, round(float(lat), 6), round(float(lon), 6)))
    return selected


@pytest.mark.parametrize("name", CASES)
def test_feature_shape_selects_expected_levels_steps_and_points(name, monkeypatch):
    shapes, expected_pairs = CASES[name]

    selected = selected_points(shapes)
    assert {(level, step) for level, step, _, _ in selected} == expected_pairs

    monkeypatch.setattr(QuadTreeSlicer, "batches_polytopes", False)
    assert selected == selected_points(shapes)
