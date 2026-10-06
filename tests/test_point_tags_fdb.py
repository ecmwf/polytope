"""Per-value tags of a multi-value nearest Point, on a structured grid (HullSlicer) and an
unstructured grid (QuadTreeSlicer). Both engines must tag every resolved point with the tag
of the value it is nearest to, and give the same result as a Union of single-value Points."""

import math

import pandas as pd
import pytest
from bulk_helpers import point_leaves

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Point, Select, Union

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
    values = None

    def selects(self):
        raise NotImplementedError

    def retrieve(self, shape):
        import pygribjump as gj

        return Polytope(datacube=gj.GribJump(), options=self.options).retrieve(Request(*self.selects(), shape))

    @pytest.mark.fdb
    def test_multi_value_point_tags(self):
        tags = [f"p{i}" for i in range(len(self.values))]
        result = tags_by_point(self.retrieve(Point(["latitude", "longitude"], self.values, method="nearest", tag=tags)))
        assert len(result) == len(self.values)
        assert all(len(t) == 1 for t in result.values())
        assert set().union(*result.values()) == set(tags)

    @pytest.mark.fdb
    def test_multi_value_point_matches_union(self):
        tags = [f"p{i}" for i in range(len(self.values))]
        multi = self.retrieve(Point(["latitude", "longitude"], self.values, method="nearest", tag=tags))
        union = self.retrieve(
            Union(
                ["latitude", "longitude"],
                *[Point(["latitude", "longitude"], [v], method="nearest", tag=t) for v, t in zip(self.values, tags)],
            )
        )
        assert tags_by_point(multi) == tags_by_point(union)


class TestPointTagsStructuredGrid(_PointTagTests):
    options = OCTAHEDRAL_OPTIONS
    values = [[0, 0], [0.2, 0.2], [1.0, 1.5]]

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


class TestPointTagsUnstructuredGrid(_PointTagTests):
    options = LAMBERT_OPTIONS
    values = [[44.25, 5.55], [43.75, 5.35], [44.0, 5.45]]

    def selects(self):
        return [
            Select("date", [pd.Timestamp("20250221T0000")]),
            Select("step", [0]),
            Select("param", ["130"]),
            Select("levtype", ["sfc"]),
        ]
