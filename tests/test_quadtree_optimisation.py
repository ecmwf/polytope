import pytest

from polytope_feature.engine.quadtree_slicer import QuadTreeSlicer
from polytope_feature.shapes import Box


class TestQuadTreeSlicer:
    def setup_method(self, method):
        import pygribjump as gj

        self.options = {
            "axis_config": [
                {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
                {
                    "axis_name": "date",
                    "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                },
                {
                    "axis_name": "values",
                    "transformations": [
                        {"name": "mapper", "type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}
                    ],
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
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
        }
        self.fdbdatacube = gj.GribJump()

    @pytest.mark.fdb
    def test_quad_tree_slicer(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        slicer.quad_tree.pprint()
        pass

    @pytest.mark.fdb
    def test_quad_tree_query_polygon(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        slicer = QuadTreeSlicer(points)
        polytope = Box(["lat", "lon"], [0, 0], [90, 45]).polytope()[0]
        results = slicer.quad_tree.query_polygon(polytope)
        assert len(results) == 5
        assert (10, 10) in [node.item for node in results]
        assert (5, 10) in [node.item for node in results]
        assert (5, 20) in [node.item for node in results]
        assert (80, 10) in [node.item for node in results]
        assert (50, 10) in [node.item for node in results]
