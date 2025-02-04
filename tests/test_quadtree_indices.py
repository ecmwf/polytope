import pytest

from polytope_feature.polytope import Polytope
from polytope_feature.shapes import Box, ConvexPolytope


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
    def test_quad_tree_slicer_extract(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10]]
        polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options={"latitude": "quadtree", "longitude": "quadtree"},
            point_cloud_options=points,
        )
        tree = self.API.engines["quadtree"].extract_single(self.API.datacube, polytope)
        assert len(tree) == 3
        assert set([leaf.index for leaf in tree]) == set(
            [
                0,
                3,
                4,
            ]
        )
        # tree.pprint()
        points = [[10, 10], [80, 10], [-5, 5], [5, 50], [5, 10], [50, 10], [2, 10], [15, 15]]
        polytope = ConvexPolytope(["latitude", "longitude"], [[-10, 1], [20, 1], [5, 20]])
        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options={"latitude": "quadtree", "longitude": "quadtree"},
            point_cloud_options=points,
        )
        tree = self.API.engines["quadtree"].extract_single(self.API.datacube, polytope)
        assert len(tree) == 4
        assert set([leaf.index for leaf in tree]) == set(
            [
                0,
                2,
                4,
                6,
            ]
        )
        # tree.pprint()
