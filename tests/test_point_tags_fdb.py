"""Per-point tags on live FDB data, on a structured grid (HullSlicer, with both the legacy leaves
and the BulkGridTensorIndexNode leaves) and an unstructured grid (QuadTreeSlicer).

Every resolved point must carry the tags of the shapes / query values that selected it: for a
nearest search only the point(s) actually nearest to a query value get that value's tag, and a
multi-value Point gives the same result as a Union of single-value Points.

The structured tests need the octahedral od/oper 20230625 data, the unstructured tests the
Lambert LAM 20250221 data."""

import math

import numpy as np
import pandas as pd
import pytest
from bulk_helpers import point_leaves

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Point, Select, Union

OCTAHEDRAL_OPTIONS = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "date", "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}]},
        {
            "axis_name": "values",
            "transformations": [
                {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
            ],
        },
        {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
        {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
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
    "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
}

LAMBERT_OPTIONS = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "date", "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}]},
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
    "engine_options": {
        "step": "hullslicer",
        "date": "hullslicer",
        "levtype": "hullslicer",
        "param": "hullslicer",
        "latitude": "quadtree",
        "longitude": "quadtree",
    },
}


def tags_by_point(result):
    tags = {}
    for leaf in point_leaves(result):
        path = leaf.flatten()
        for lat in path["latitude"]:
            for lon in path["longitude"]:
                tags.setdefault((lat, lon), set()).update(leaf.tags)
    return tags


class _PointTagTests:
    options = None
    # Far apart query values, nearest to different grid points
    values = None
    # Two query values whose candidate grid points overlap, nearest to different grid points
    close_values = None
    box = None

    def selects(self):
        raise NotImplementedError

    def retrieve(self, shape, **options):
        import pygribjump as gj

        api = Polytope(datacube=gj.GribJump(), options=dict(self.options, **options))
        return api.retrieve(Request(*self.selects(), shape))

    def multi(self, values, tags, **options):
        return self.retrieve(Point(["latitude", "longitude"], values, method="nearest", tag=tags), **options)

    def union(self, values, tags, **options):
        points = [Point(["latitude", "longitude"], [v], method="nearest", tag=t) for v, t in zip(values, tags)]
        return self.retrieve(Union(["latitude", "longitude"], *points), **options)

    def check_one_tag_per_value(self, result, values, tags):
        found = tags_by_point(result)
        assert len(found) == len(values)
        assert all(len(t) == 1 for t in found.values())
        assert set().union(*found.values()) == set(tags)
        return found

    @pytest.mark.fdb
    def test_multi_value_point_tags(self):
        tags = [f"p{i}" for i in range(len(self.values))]
        self.check_one_tag_per_value(self.multi(self.values, tags), self.values, tags)

    @pytest.mark.fdb
    def test_multi_value_point_matches_union(self):
        tags = [f"p{i}" for i in range(len(self.values))]
        assert tags_by_point(self.multi(self.values, tags)) == tags_by_point(self.union(self.values, tags))

    @pytest.mark.fdb
    def test_close_values_keep_their_own_tag(self):
        tags = ["A", "B"]
        for result in (self.multi(self.close_values, tags), self.union(self.close_values, tags)):
            self.check_one_tag_per_value(result, self.close_values, tags)

    @pytest.mark.fdb
    def test_same_nearest_point_gets_all_tags(self):
        value = self.values[0]
        found = tags_by_point(self.multi([value, value], ["A", "B"]))
        assert list(found.values()) == [{"A", "B"}]

    @pytest.mark.fdb
    def test_single_tag_for_all_values(self):
        found = tags_by_point(self.multi(self.values, "shared"))
        assert len(found) == len(self.values)
        assert all(t == {"shared"} for t in found.values())

    @pytest.mark.fdb
    def test_untagged_points(self):
        found = tags_by_point(self.multi(self.values, None))
        assert len(found) == len(self.values)
        assert all(t == set() for t in found.values())

    @pytest.mark.fdb
    def test_box_tag_on_every_point(self):
        found = tags_by_point(self.retrieve(Box(["latitude", "longitude"], *self.box, tag="box")))
        assert len(found) > 1
        assert all(t == {"box"} for t in found.values())

    @pytest.mark.fdb
    def test_many_random_values_match_union(self):
        rng = np.random.default_rng(0)
        lows, highs = np.min(self.values, axis=0), np.max(self.values, axis=0)
        values = rng.uniform(lows, highs, size=(40, 2)).tolist()
        tags = [f"r{i}" for i in range(len(values))]
        multi = tags_by_point(self.multi(values, tags))
        assert multi == tags_by_point(self.union(values, tags))
        # every value's tag ends up on exactly one point
        counts = {}
        for point_tags in multi.values():
            for tag in point_tags:
                counts[tag] = counts.get(tag, 0) + 1
        assert counts == {tag: 1 for tag in tags}


class TestPointTagsStructuredGrid(_PointTagTests):
    options = OCTAHEDRAL_OPTIONS
    values = [[0, 0], [0.2, 0.2], [1.0, 1.5]]
    close_values = [[0, 0], [0.0, 0.08]]
    box = ([0, 0], [0.2, 0.2])

    def selects(self):
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


class TestPointTagsStructuredBulkGrid(TestPointTagsStructuredGrid):
    """Same checks with the latitude/longitude layers folded into a BulkGridTensorIndexNode."""

    options = dict(OCTAHEDRAL_OPTIONS, bulk_grid_leaves=True)

    @pytest.mark.fdb
    def test_leaves_are_bulk_grid_nodes(self):
        from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode

        result = self.multi(self.values, ["A", "B", "C"])
        assert all(isinstance(leaf, BulkGridTensorIndexNode) for leaf in result.leaves)

    @pytest.mark.fdb
    def test_matches_legacy_leaves(self):
        tags = [f"p{i}" for i in range(len(self.values))]
        bulk = tags_by_point(self.multi(self.values, tags))
        legacy = tags_by_point(self.multi(self.values, tags, bulk_grid_leaves=False))
        assert bulk == legacy


class TestPointTagsUnstructuredGrid(_PointTagTests):
    options = LAMBERT_OPTIONS
    values = [[44.25, 5.55], [43.75, 5.35], [44.0, 5.45]]
    close_values = [[44.0, 5.45], [44.0, 5.456]]
    box = ([44, 5.5], [44.05, 5.52])

    def selects(self):
        return [
            Select("date", [pd.Timestamp("20250221T0000")]),
            Select("step", [0]),
            Select("param", ["130"]),
            Select("levtype", ["sfc"]),
        ]

    @pytest.mark.fdb
    def test_k_nearest_points_carry_the_value_tag(self):
        shape = Point(["latitude", "longitude"], self.values[:2], method="nearest", k=4, tag=["A", "B"])
        found = tags_by_point(self.retrieve(shape))
        assert len(found) == 8
        assert sorted(len(t) for t in found.values()) == [1] * 8
        assert sum(t == {"A"} for t in found.values()) == 4
