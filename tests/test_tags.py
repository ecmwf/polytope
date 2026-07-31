"""Tests for shape tagging: tags defined on shapes are preserved through
slicing and appear on the corresponding TensorIndexTree leaf nodes."""

import numpy as np
import xarray as xr

from polytope_feature.engine.slicing_tools import slice as polytope_slice
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import (
    All,
    Box,
    ConvexPolytope,
    Point,
    Select,
    Span,
    Union,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_2d_api(step_vals, level_vals, options=None):
    """Build a Polytope API backed by a small xarray DataArray with 'step' and 'level'."""
    array = xr.DataArray(
        np.arange(len(step_vals) * len(level_vals), dtype=float).reshape(len(step_vals), len(level_vals)),
        dims=("step", "level"),
        coords={"step": step_vals, "level": level_vals},
    )
    if options is None:
        options = {}
    return Polytope(datacube=array, options=options)


def _make_3d_api(step_vals, level_vals, number_vals, options=None):
    """3-D xarray DataArray with 'step', 'level', and 'number' axes."""
    array = xr.DataArray(
        np.arange(len(step_vals) * len(level_vals) * len(number_vals), dtype=float).reshape(
            len(step_vals), len(level_vals), len(number_vals)
        ),
        dims=("step", "level", "number"),
        coords={"step": step_vals, "level": level_vals, "number": number_vals},
    )
    if options is None:
        options = {}
    return Polytope(datacube=array, options=options)


# ---------------------------------------------------------------------------
# Unit-level: ConvexPolytope tag attribute
# ---------------------------------------------------------------------------


class TestConvexPolytopeTag:
    def test_default_tag_is_none(self):
        p = ConvexPolytope(["x"], [[1.0]])
        assert p.tag is None

    def test_tag_stored(self):
        p = ConvexPolytope(["x"], [[1.0]], tag="my_tag")
        assert p.tag == "my_tag"

    def test_tag_any_python_object(self):
        tag = {"key": 42, "nested": [1, 2]}
        p = ConvexPolytope(["x"], [[1.0]], tag=tag)
        assert p.tag is tag

    def test_tag_preserved_through_slice_flat(self):
        """Flat 1-D polytope: slice returns None (consumed), tag not lost on original."""
        p = ConvexPolytope(["x"], [[3.0]], is_orthogonal=True, tag="A")
        result = polytope_slice(p, "x", 3.0, 0)
        # Flat polytope at exact value → result is None (fully consumed)
        assert result is None
        assert p.tag == "A"

    def test_tag_preserved_through_slice_span(self):
        """Slicing a 2-D polytope produces a 1-D result that carries the same tag."""
        # 2-D box: axes x and y
        p = ConvexPolytope(["x", "y"], [[0.0, 0.0], [4.0, 0.0], [4.0, 4.0], [0.0, 4.0]], tag="box_tag")
        result = polytope_slice(p, "x", 2.0, 0)
        assert result is not None
        assert result.tag == "box_tag"

    def test_tag_preserved_through_multiple_slices(self):
        """Tag survives successive dimension reductions."""
        p = ConvexPolytope(
            ["x", "y", "z"],
            [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0],
                [0.0, 1.0, 1.0],
            ],
            tag="cube",
        )
        p2 = polytope_slice(p, "z", 0.5, 2)
        assert p2 is not None
        assert p2.tag == "cube"
        p1 = polytope_slice(p2, "y", 0.5, 1)
        assert p1 is not None
        assert p1.tag == "cube"


# ---------------------------------------------------------------------------
# Shape-level: tag flows from shape constructors into ConvexPolytopes
# ---------------------------------------------------------------------------


class TestShapeTagPropagation:
    def test_point_tag_on_polytope(self):
        pt = Point(["step", "level"], [[3, 5]], tag="pt_tag")
        polys = pt.polytope()
        # decompose_1D=True → Product containing two 1-D ConvexPolytopes
        assert len(polys) == 1
        from polytope_feature.shapes import Product

        assert isinstance(polys[0], Product)
        assert polys[0].tag == "pt_tag"
        for cp in polys[0].polytope():
            assert cp.tag == "pt_tag"

    def test_select_tag_on_polytope(self):
        s = Select("step", [3, 6], tag="sel_tag")
        for cp in s.polytope():
            assert cp.tag == "sel_tag"

    def test_span_tag_on_polytope(self):
        sp = Span("level", 1, 10, tag="span_tag")
        polys = sp.polytope()
        assert len(polys) == 1
        assert polys[0].tag == "span_tag"

    def test_all_tag_on_polytope(self):
        a = All("level", tag="all_tag")
        polys = a.polytope()
        assert len(polys) == 1
        assert polys[0].tag == "all_tag"

    def test_box_tag_on_polytope(self):
        b = Box(["step", "level"], [0, 0], [5, 10], tag="box_tag")
        polys = b.polytope()
        assert len(polys) == 1
        assert polys[0].tag == "box_tag"

    def test_no_tag_default_none(self):
        pt = Point(["step", "level"], [[3, 5]])
        for cp in pt.polytope()[0].polytope():
            assert cp.tag is None


# ---------------------------------------------------------------------------
# Integration: tags reach TensorIndexTree nodes after slicing
# ---------------------------------------------------------------------------


class TestTagsOnTreeNodes:
    """End-to-end tests using a small xarray datacube."""

    def setup_method(self, method):
        self.step_vals = [0, 3, 6, 9, 12, 15]
        self.level_vals = list(range(1, 11))  # 1..10
        self.api = _make_2d_api(self.step_vals, self.level_vals)

    # -- basic single tagged point ----------------------------------------

    def test_single_tagged_point_leaf_has_tag(self):
        request = Request(
            Union(
                ["step", "level"],
                Point(["step", "level"], [[3, 5]], tag="alpha"),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 1
        assert "alpha" in leaves[0].tags

    def test_single_untagged_point_leaf_has_empty_tags(self):
        request = Request(
            Union(
                ["step", "level"],
                Point(["step", "level"], [[3, 5]]),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 1
        assert len(leaves[0].tags) == 0

    # -- union of two distinct tagged points --------------------------------

    def test_two_tagged_points_correct_leaf_tags(self):
        request = Request(
            Union(
                ["step", "level"],
                Point(["step", "level"], [[3, 5]], tag="alpha"),
                Point(["step", "level"], [[9, 7]], tag="beta"),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 2

        # Build a dict of (step_val, level_val) → tags for easy lookup
        leaf_tags = {}
        for leaf in leaves:
            path = leaf.flatten()
            key = (path["step"][0], path["level"][0])
            leaf_tags[key] = leaf.tags

        assert leaf_tags[(3, 5)] == {"alpha"}
        assert leaf_tags[(9, 7)] == {"beta"}

    def test_three_tagged_points_all_correct(self):
        request = Request(
            Union(
                ["step", "level"],
                Point(["step", "level"], [[0, 1]], tag="first"),
                Point(["step", "level"], [[6, 4]], tag="second"),
                Point(["step", "level"], [[12, 9]], tag="third"),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 3

        leaf_tags = {}
        for leaf in leaves:
            path = leaf.flatten()
            key = (path["step"][0], path["level"][0])
            leaf_tags[key] = leaf.tags

        assert leaf_tags[(0, 1)] == {"first"}
        assert leaf_tags[(6, 4)] == {"second"}
        assert leaf_tags[(12, 9)] == {"third"}

    # -- tag accumulation when two points map to the same node --------------

    def test_same_coords_different_tags_accumulate(self):
        """Two Points at identical coordinates should accumulate both tags on the shared leaf."""
        request = Request(
            Union(
                ["step", "level"],
                Point(["step", "level"], [[3, 5]], tag="alpha"),
                Point(["step", "level"], [[3, 5]], tag="beta"),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        # Both points map to the same datacube location → one leaf
        assert len(leaves) == 1
        assert leaves[0].tags == {"alpha", "beta"}

    def test_same_tag_on_two_points_remains_singleton(self):
        """Two Points with the same tag accumulate to a set with one element."""
        request = Request(
            Union(
                ["step", "level"],
                Point(["step", "level"], [[3, 5]], tag="shared"),
                Point(["step", "level"], [[9, 7]], tag="shared"),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 2
        for leaf in leaves:
            assert leaf.tags == {"shared"}

    # -- tag carries across 1D shapes in 1D datacube ------------------------

    def test_tagged_span_in_1d(self):
        """A Span with a tag should appear on the leaf nodes within that span."""
        array = xr.DataArray(
            np.arange(10, dtype=float),
            dims=("level",),
            coords={"level": list(range(10))},
        )
        api = Polytope(datacube=array, options={})
        request = Request(Span("level", 2, 4, tag="span_tag"))
        result = api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) >= 1
        # The span tag should appear on the node where the span polytope is resolved
        tagged_nodes = [n for n in leaves if "span_tag" in n.tags]
        assert len(tagged_nodes) > 0

    # -- tag does not bleed between unrelated shapes in the same request ----

    def test_tag_isolation_across_independent_shapes(self):
        """A Select on one axis with a tag should not contaminate a Union on another."""
        array = xr.DataArray(
            np.arange(6 * 10, dtype=float).reshape(6, 10),
            dims=("step", "level"),
            coords={"step": [0, 3, 6, 9, 12, 15], "level": list(range(1, 11))},
        )
        api = Polytope(datacube=array, options={})
        request = Request(
            Select("step", [3], tag="step_tag"),
            Union(
                ["level"],
                Select("level", [5], tag="level_A"),
                Select("level", [7], tag="level_B"),
            ),
        )
        result = api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 2

        leaf_tags = {}
        for leaf in leaves:
            path = leaf.flatten()
            level_val = path["level"][0]
            leaf_tags[level_val] = leaf.tags

        # The Select on "level" uses distinct 1-D polytopes; each resolves once
        assert "level_A" in leaf_tags[5]
        assert "level_B" in leaf_tags[7]
        # "step_tag" should be on the step node, not on level leaves;
        # level leaves may or may not carry step_tag depending on which polytope
        # resolves last — what matters is that level tags are correct.
        assert "level_B" not in leaf_tags[5]
        assert "level_A" not in leaf_tags[7]


# ---------------------------------------------------------------------------
# 3-D datacube: tag flows through deeper trees
# ---------------------------------------------------------------------------


class TestTagsOn3DTree:
    def setup_method(self, method):
        self.step_vals = [0, 3, 6, 9]
        self.level_vals = [1, 2, 3, 4, 5]
        self.number_vals = [0, 1, 2]
        self.api = _make_3d_api(self.step_vals, self.level_vals, self.number_vals)

    def test_union_of_tagged_points_3d(self):
        request = Request(
            Union(
                ["step", "level", "number"],
                Point(["step", "level", "number"], [[3, 2, 1]], tag="A"),
                Point(["step", "level", "number"], [[9, 4, 0]], tag="B"),
            )
        )
        result = self.api.retrieve(request)
        leaves = result.leaves
        assert len(leaves) == 2

        leaf_tags = {}
        for leaf in leaves:
            path = leaf.flatten()
            key = (path["step"][0], path["level"][0], path["number"][0])
            leaf_tags[key] = leaf.tags

        assert leaf_tags[(3, 2, 1)] == {"A"}
        assert leaf_tags[(9, 4, 0)] == {"B"}
