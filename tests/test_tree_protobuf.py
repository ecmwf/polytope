class TestTreeProtobuf:

    def test_protobuf_tree(self):
        import polytope.datacube.index_tree_pb2 as pb2

        node = pb2.Node()
        node2 = pb2.Node()
        node3 = pb2.Node()
        node.int_val = 1
        node2.int_val = 2
        node3.int_val = 3
        node4 = pb2.Node()
        node4.int_val = 4
        node3.children.extend([node4])
        node5 = node.children.add()
        node5.int_val = 5
        node.children.extend([node2, node3])

        assert len(node.children) == 3
        assert len(node.children[2].children) == 1
