import numpy as np
import pandas as pd

from polytope.datacube.backends.mock import MockDatacube
from polytope.datacube.datacube_axis import (
    FloatDatacubeAxis,
    IntDatacubeAxis,
    PandasTimedeltaDatacubeAxis,
    PandasTimestampDatacubeAxis,
    UnsliceableDatacubeAxis,
)
from polytope.datacube.tensor_index_tree import TensorIndexTree
from polytope.datacube.tree_encoding import decode_tree, encode_tree


class TestEncoder:
    def setup_method(self):
        self.fake_tree = TensorIndexTree()
        child_ax1 = IntDatacubeAxis()
        child_ax1.name = "ax1"
        child1 = TensorIndexTree(child_ax1, (1,))
        child_ax2 = PandasTimestampDatacubeAxis()
        child_ax2.name = "timestamp_ax"
        child2 = TensorIndexTree(child_ax2, (pd.Timestamp("2000-01-01 00:00:00"),))
        grandchild_ax1 = FloatDatacubeAxis()
        grandchild_ax1.name = "ax2"
        grandchild1 = TensorIndexTree(grandchild_ax1, (2.3,))
        grandchild_ax2 = UnsliceableDatacubeAxis()
        grandchild_ax2.name = "ax3"
        grandchild2 = TensorIndexTree(grandchild_ax2, ("var1",))
        grandchild_ax3 = PandasTimedeltaDatacubeAxis()
        grandchild_ax3.name = "timedelta_ax"
        grandchild3 = TensorIndexTree(grandchild_ax3, (np.timedelta64(0, "s"),))
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

    def test_encoding(self):
        encode_tree(self.fake_tree)
        decoded_tree = decode_tree(self.datacube)
        decoded_tree.pprint()
        assert decoded_tree.leaves[0].result_size == [1, 1, 1]
