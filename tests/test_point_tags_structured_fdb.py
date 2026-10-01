"""
Tag-correctness tests for the Point shape against a *structured* (regular)
octahedral/reduced-Gaussian grid, retrieved live from FDB via the HullSlicer
engine.

"Structured" here means the grid is handled by HullSlicer (axis-by-axis
binary search), as opposed to the QuadTreeSlicer used for genuinely
unstructured/irregular grids (see test_point_tags_unstructured_fdb.py).

These tests verify that tags attached to a Point shape's individual values
are returned on the correct corresponding TensorIndexTree leaf — i.e. that
tag_i ends up on the leaf resolving values[i], and only that leaf.

Run with:
    pytest tests/test_point_tags_structured_fdb.py -v -s -m fdb
"""

import pandas as pd
import pytest

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select, Union

OCTAHEDRAL_OPTIONS = {
    "axis_config": [
        {
            "axis_name": "step",
            "transformations": [{"name": "type_change", "type": "int"}],
        },
        {
            "axis_name": "number",
            "transformations": [{"name": "type_change", "type": "int"}],
        },
        {
            "axis_name": "date",
            "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        },
        {
            "axis_name": "values",
            "transformations": [
                {
                    "name": "mapper",
                    "type": "octahedral",
                    "resolution": 1280,
                    "axes": ["latitude", "longitude"],
                }
            ],
        },
        {
            "axis_name": "latitude",
            "transformations": [{"name": "reverse", "is_reverse": True}],
        },
        {
            "axis_name": "longitude",
            "transformations": [{"name": "cyclic", "range": [0, 360]}],
        },
    ],
    "compressed_axes_config": [
        "longitude",
        "latitude",
        "levtype",
        "step",
        "date",
        "domain",
        "expver",
        "param",
        "class",
        "stream",
        "type",
    ],
    "pre_path": {
        "class": "od",
        "expver": "0001",
        "levtype": "sfc",
        "stream": "oper",
    },
    # No "engine_options" override => everything (including latitude/longitude)
    # defaults to "hullslicer" since the octahedral mapper is not irregular.
}


class TestPointTagsStructuredGrid:
    """Live-FDB tag tests against a real octahedral grid (class=od, 20230625)."""

    def _build_api(self):
        import pygribjump as gj

        fdbdatacube = gj.GribJump()
        return Polytope(datacube=fdbdatacube, options=OCTAHEDRAL_OPTIONS)

    def _base_selects(self):
        return [
            Select("step", [0]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20230625T120000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["an"]),
        ]

    # -- control: Union of distinct tagged single-value Points -----------
    # This is the established, recommended pattern and is expected to always
    # resolve each point's tag onto its own, correct leaf.

    @pytest.mark.fdb
    def test_union_of_single_value_points_tags_are_correct(self, capsys):
        api = self._build_api()
        request = Request(
            *self._base_selects(),
            Union(
                ["latitude", "longitude"],
                Point(["latitude", "longitude"], [[0, 0]], method="nearest", tag="pointA"),
                Point(["latitude", "longitude"], [[0.2, 0.2]], method="nearest", tag="pointB"),
            ),
        )
        result = api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 2

        tag_by_leaf = {}
        for leaf in leaves:
            path = leaf.flatten()
            key = (path["latitude"][0], path["longitude"][0])
            tag_by_leaf[key] = leaf.tags

        with capsys.disabled():
            print("\n[structured/hullslicer] Union-of-Points leaf tags:", tag_by_leaf)

        all_tags = set().union(*tag_by_leaf.values())
        assert all_tags == {"pointA", "pointB"}
        # Each tag should appear on exactly one leaf (no bleeding between points).
        for tags in tag_by_leaf.values():
            assert len(tags) == 1

    # -- the case under test: ONE Point shape holding multiple values ----
    # with a per-value tag list (`tag=[...]`), NOT wrapped in Union.
    #
    # Each requested (lat, lon) value, together with its own tag, is tracked
    # through the datacube's nearest_search registry (see
    # polytope_feature/polytope.py and
    # polytope_feature/datacube/backends/fdb.py::nearest_lat_lon_search),
    # which re-attaches the correct tag to each resolved leaf once the real
    # nearest match for each query point is known, instead of relying on
    # whichever polytope happened to be iterated while HullSlicer built
    # speculative candidate branches.
    @pytest.mark.fdb
    def test_single_point_shape_multiple_values_tags_are_correct(self, capsys):
        api = self._build_api()
        values = [[0, 0], [0.2, 0.2]]
        tags = ["pointA", "pointB"]
        request = Request(
            *self._base_selects(),
            Point(["latitude", "longitude"], values, method="nearest", tag=tags),
        )
        result = api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 2

        tag_by_leaf = {}
        for leaf in leaves:
            path = leaf.flatten()
            key = (path["latitude"][0], path["longitude"][0])
            tag_by_leaf[key] = leaf.tags

        with capsys.disabled():
            print("\n[structured/hullslicer] single multi-value Point leaf tags:", tag_by_leaf)

        # Each leaf should carry exactly one tag, and the two tags should be
        # distinct (one per requested value) rather than both leaves sharing
        # the same tag.
        all_tag_sets = list(tag_by_leaf.values())
        assert all(len(tags_) == 1 for tags_ in all_tag_sets)
        merged = set().union(*all_tag_sets)
        assert merged == {"pointA", "pointB"}
