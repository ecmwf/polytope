import polytope_feature.datacube.index_tree_pb2 as pb2


class TestTreeProtobuf:
    def test_protobuf_tree(self):
        node = pb2.Node()
        node2 = pb2.Node()
        node3 = pb2.Node()
        val1 = "1"
        node.value.append(val1)
        val2 = "2"
        node2.value.append(val2)
        val3 = "3"
        node3.value.append(val3)
        node4 = pb2.Node()
        val4 = "4"
        node4.value.append(val4)
        node3.children.extend([node4])
        node5 = node.children.add()
        val5 = "5"
        node5.value.append(val5)
        node.children.extend([node2, node3])

        assert len(node.children) == 3
        assert len(node.children[2].children) == 1
