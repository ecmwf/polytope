import pytest

from polytope_feature.datacube.backends.mock import MockDatacube
from polytope_feature.datacube.datacube_axis import (
    FloatDatacubeAxis,
    IntDatacubeAxis,
    PandasTimedeltaDatacubeAxis,
    PandasTimestampDatacubeAxis,
    UnsliceableDatacubeAxis,
)
from polytope_feature.datacube.tensor_index_tree import TensorIndexTree
from polytope_feature.datacube.tree_encoding import decode_tree, encode_tree


class TestEncoder:
    def setup_method(self):
        self.fake_tree = TensorIndexTree()
        child_ax1 = IntDatacubeAxis()
        child_ax1.name = "ax1"
        child1 = TensorIndexTree(child_ax1, ("1",))
        child_ax2 = PandasTimestampDatacubeAxis()
        child_ax2.name = "timestamp_ax"
        child2 = TensorIndexTree(child_ax2, ("string",))
        grandchild_ax1 = FloatDatacubeAxis()
        grandchild_ax1.name = "ax2"
        grandchild1 = TensorIndexTree(grandchild_ax1, ("2.3",))
        grandchild_ax2 = UnsliceableDatacubeAxis()
        grandchild_ax2.name = "ax3"
        grandchild2 = TensorIndexTree(grandchild_ax2, ("var1",))
        grandchild_ax3 = PandasTimedeltaDatacubeAxis()
        grandchild_ax3.name = "timedelta_ax"
        grandchild3 = TensorIndexTree(grandchild_ax3, ("0.0001",))
        child1.add_child(grandchild2)
        child1.add_child(grandchild1)
        child2.add_child(grandchild3)
        # TODO: test the timestamp and timedelta axes too
        self.fake_tree.add_child(child1)
        self.fake_tree.add_child(child2)
        self.datacube = MockDatacube({"ax1": 1, "ax2": 1, "ax3": 1, "timestamp_ax": 1, "timedelta_ax": 1})
        self.datacube._axes = {
            "ax1": child_ax1,
            "ax2": grandchild_ax1,
            "ax3": grandchild_ax2,
            "timestamp_ax": child_ax2,
            "timedelta_ax": grandchild_ax3,
        }

    @pytest.mark.fdb
    def test_encoding(self):
        import pygribjump as gj

        from polytope_feature.engine.hullslicer import HullSlicer
        from polytope_feature.polytope import Polytope

        self.options = {
            "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
        }
        self.fdbdatacube = gj.GribJump()
        self.slicer = HullSlicer()
        self.API = Polytope(
            datacube=self.fdbdatacube,
            engine=self.slicer,
            options=self.options,
        )
        fdb_datacube = self.API.datacube
        fdb_datacube.prep_tree_encoding(self.fake_tree)
        encoded_bytes = encode_tree(self.fake_tree)
        decoded_tree = decode_tree(self.datacube, encoded_bytes)
        decoded_tree.pprint()
        assert decoded_tree.leaves[0].result_size == [1, 1]
