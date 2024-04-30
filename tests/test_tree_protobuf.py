import polytope.datacube.index_tree_pb2 as pb2


class TestTreeProtobuf:
    def test_protobuf_tree(self):
        node = pb2.Node()
        node2 = pb2.Node()
        node3 = pb2.Node()
        val1 = pb2.Value()
        val2 = pb2.Value()
        val3 = pb2.Value()
        val1.int_val = 1
        node.value.append(val1)
        val2.int_val = 2
        node2.value.append(val2)
        val3.int_val = 3
        node3.value.append(val3)
        node4 = pb2.Node()
        val4 = pb2.Value()
        val4.int_val = 4
        node4.value.append(val4)
        node3.children.extend([node4])
        node5 = node.children.add()
        val5 = pb2.Value()
        val5.int_val = 5
        node5.value.append(val5)
        node.children.extend([node2, node3])

        assert len(node.children) == 3
        assert len(node.children[2].children) == 1
