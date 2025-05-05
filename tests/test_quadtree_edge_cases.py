import pytest

from polytope_feature.polytope import Polytope
from polytope_feature.shapes import Box


class TestQuadTreeSlicer:
    def setup_method(self, method):
        import pygribjump as gj

        # self.options = {
        #     "axis_config": [
        #         {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        #         {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        #         {
        #             "axis_name": "date",
        #             "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        #         },
        #         {
        #             "axis_name": "values",
        #             "transformations": [
        #                 {"name": "mapper", "type": "unstructured", "resolution": 1280,
        #                     "axes": ["latitude", "longitude"], "points": points}
        #             ],
        #         },
        #     ],
        #     "compressed_axes_config": [
        #         "longitude",
        #         "latitude",
        #         "levtype",
        #         "step",
        #         "date",
        #         "domain",
        #         "expver",
        #         "param",
        #         "class",
        #         "stream",
        #         "type",
        #     ],
        #     "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
        # }
        self.fdbdatacube = gj.GribJump()

    @pytest.mark.fdb
    def test_quad_tree_slicer_extract(self):
        points = [[10, 10], [80, 10], [-5, 5], [5, 20], [5, 10], [50, 10], [0.035149384216, 0.0]]
        polytope = Box(["latitude", "longitude"], [0, 0], [15, 15]).polytope()[0]
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
                        {"name": "mapper", "type": "unstructured", "resolution": 1280,
                            "axes": ["latitude", "longitude"], "points": points}
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
        self.API = Polytope(
            datacube=self.fdbdatacube,
            options=self.options,
            engine_options={"latitude": "quadtree", "longitude": "quadtree"},
            # point_cloud_options=points,
        )
        tree = self.API.engines["quadtree"].extract(self.API.datacube, [polytope])
        tree.pprint()
        assert len(tree.leaves) == 3
        assert set([leaf.flatten()["values"] for leaf in tree.leaves]) == set([(0,), (4,), (6,)])
