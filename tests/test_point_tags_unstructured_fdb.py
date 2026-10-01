"""
Tag-correctness tests for the Point shape against a genuinely *unstructured*
(irregular) grid -- a Lambert-conformal LAM grid retrieved live from FDB via
the QuadTreeSlicer engine.

"Unstructured" here means the grid is backed by a point cloud and resolved
via the QuadTree nearest-neighbour engine (see
polytope_feature/engine/quadtree_slicer.py), as opposed to HullSlicer used
for structured/regular grids (see test_point_tags_structured_fdb.py).

These tests verify that tags attached to a Point shape's individual values
are returned on the correct corresponding TensorIndexTree leaf.

Run with:
    pytest tests/test_point_tags_unstructured_fdb.py -v -s -m fdb
"""

import math

import pandas as pd
import pytest

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select, Union

ENGINE_OPTIONS = {
    "step": "hullslicer",
    "date": "hullslicer",
    "levtype": "hullslicer",
    "param": "hullslicer",
    "latitude": "quadtree",
    "longitude": "quadtree",
}

LAMBERT_LAM_OPTIONS = {
    "axis_config": [
        {
            "axis_name": "step",
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
                    "type": "lambert_conformal",
                    "resolution": 0,
                    "axes": ["latitude", "longitude"],
                    "md5_hash": "3c528b5fd68ca692a8922cbded813465",
                    "is_spherical": True,
                    "radius": 6371229,
                    "nv": 0,
                    "nx": 1489,
                    "ny": 1489,
                    "LoVInDegrees": 1.93697,
                    "Dx": 500,
                    "Dy": 500,
                    "latFirstInRadians": ((43.6409 + 2.9710306719721302e-05) / 180) * math.pi,
                    "lonFirstInRadians": ((357.32 - 0.00024761029651987343) / 180) * math.pi,
                    "LoVInRadians": (1.93697 / 180) * math.pi,
                    "Latin1InRadians": (47.082971 / 180) * math.pi,
                    "Latin2InRadians": (47.082971 / 180) * math.pi,
                    "LaDInRadians": (47.082971 / 180) * math.pi,
                }
            ],
        },
    ],
    "pre_path": {"date": "20250221"},
    "engine_options": ENGINE_OPTIONS,
}


class TestPointTagsUnstructuredGrid:
    """Live-FDB tag tests against a real Lambert-conformal LAM grid (date=20250221)."""

    def _build_api(self):
        import pygribjump as gj

        fdbdatacube = gj.GribJump()
        return Polytope(datacube=fdbdatacube, options=LAMBERT_LAM_OPTIONS)

    def _base_selects(self):
        return [
            Select("date", [pd.Timestamp("20250221T0000")]),
            Select("step", [0]),
            Select("param", ["130"]),
            Select("levtype", ["sfc"]),
        ]

    # -- control: Union of distinct tagged single-value Points -----------
    # Established, recommended pattern; expected to resolve each point's tag
    # onto its own, correct leaf.

    @pytest.mark.fdb
    def test_union_of_single_value_points_tags_are_correct(self, capsys):
        api = self._build_api()
        request = Request(
            *self._base_selects(),
            Union(
                ["latitude", "longitude"],
                Point(["latitude", "longitude"], [[44.25, 5.55]], method="nearest", tag="pointA"),
                Point(["latitude", "longitude"], [[43.75, 5.35]], method="nearest", tag="pointB"),
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
            print("\n[unstructured/quadtree] Union-of-Points leaf tags:", tag_by_leaf)

        all_tags = set().union(*tag_by_leaf.values())
        assert all_tags == {"pointA", "pointB"}
        for tags in tag_by_leaf.values():
            assert len(tags) == 1

    # -- the case under test: ONE Point shape holding multiple values ----
    # with a per-value tag list (`tag=[...]`), NOT wrapped in Union.
    #
    # Each requested (lat, lon) value, together with its own tag, is carried
    # on its own ConvexPolytope through to QuadTreeSlicer, which now resolves
    # and tags each polytope's own k-nearest-neighbour result independently
    # (see polytope_feature/engine/quadtree_slicer.py), instead of relying on
    # the shared, global `datacube.nearest_search` registry. This verifies
    # that a single multi-value Point shape (the batched/performant form used
    # for large point lists, c.f. test_perf_nn_many_points_octahedral_fdb.py)
    # attributes each resolved leaf with its own, correct tag.
    @pytest.mark.fdb
    def test_single_point_shape_multiple_values_tags_are_correct(self, capsys):
        api = self._build_api()
        values = [[44.25, 5.55], [43.75, 5.35]]
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
            print("\n[unstructured/quadtree] single multi-value Point leaf tags:", tag_by_leaf)

        all_tag_sets = list(tag_by_leaf.values())
        assert all(len(tags_) == 1 for tags_ in all_tag_sets)
        merged = set().union(*all_tag_sets)
        assert merged == {"pointA", "pointB"}
