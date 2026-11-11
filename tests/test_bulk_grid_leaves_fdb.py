import numpy as np
import pandas as pd
import pytest
from bulk_helpers import point_leaves

from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Select


class TestBulkGridLeaves:
    def setup_method(self, method):
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

    def retrieve(self):
        import pygribjump as gj

        request = Request(
            Select("step", [0, 1, 2]),
            Select("levtype", ["sfc"]),
            Select("date", [pd.Timestamp("20240103T0000")]),
            Select("domain", ["g"]),
            Select("expver", ["0001"]),
            Select("param", ["167"]),
            Select("class", ["od"]),
            Select("stream", ["oper"]),
            Select("type", ["fc"]),
            # crosses the cyclic longitude seam
            Box(["latitude", "longitude"], [40, -2], [42, 2]),
        )
        return Polytope(datacube=gj.GribJump(), options=self.options).retrieve(request)

    @staticmethod
    def points(tree):
        # (lat, lon) -> values of the 3 compressed steps
        points = {}
        for leaf in tree.leaves:
            values = np.asarray(leaf.result, dtype=np.float64)
            for i, (lat, lon) in enumerate(leaf.coordinates):
                points[(round(lat, 6), round(lon, 6))] = tuple(values[:, i])
        return points

    @pytest.mark.fdb
    def test_one_bulk_grid_node_holds_the_whole_box(self):
        """The box crosses the cyclic longitude seam: its rows fold into one node of 868 points."""
        grid = self.retrieve()

        grid_leaves = grid.leaves
        assert len(grid_leaves) == 1
        grid_node = grid_leaves[0]
        assert isinstance(grid_node, BulkGridTensorIndexNode)
        assert grid_node.point_count == len(point_leaves(grid)) == 868
        assert grid_node.point_count == sum(len(lons) for lons in grid_node.lon_values)
        # one values array per compressed step, each value belonging to its own point
        assert len(grid_node.result) == 3
        points = self.points(grid)
        assert len(points) == 868
        assert all(len(values) == 3 and not np.isnan(values).any() for values in points.values())
