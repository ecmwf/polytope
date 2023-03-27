from sortedcontainers import SortedList

from polytope.datacube.datacube_axis import IntAxis
from polytope.datacube.datacube_request_tree import DatacubeRequestTree


class TestRequestTree():

    def setup_method(self, method):
        pass

    def test_init(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "child1"
        axis3.name = "child2"
        grandchild1 = DatacubeRequestTree(axis=axis1)
        child1 = DatacubeRequestTree(axis=axis2)
        child2 = DatacubeRequestTree(axis=axis3)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        root_node.add_child(child2)
        child1.add_child(grandchild1)
        assert child1.children == SortedList([grandchild1])

    def test_add_child(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis1.name = "grandchild"
        axis2.name = "child"
        root_node = DatacubeRequestTree()
        child = DatacubeRequestTree(axis=axis2)
        root_node.add_child(child)
        assert root_node.children == SortedList([child])
        root_node = DatacubeRequestTree()
        grandchild = DatacubeRequestTree(axis=axis1)
        child = DatacubeRequestTree(axis=axis2)
        root_node.add_child(child)
        child.add_child(grandchild)
        assert SortedList([grandchild]) in [c.children for c in root_node.children]

    def test_get_parent(self):
        axis1 = IntAxis()
        axis1.name = "child"
        child = DatacubeRequestTree(axis=axis1)
        root_node = DatacubeRequestTree()
        root_node.add_child(child)
        assert child.parent == root_node

    def test_find_child(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis1.name = "child1"
        axis2.name = "child2"
        child1 = DatacubeRequestTree(axis=axis1)
        child2 = DatacubeRequestTree(axis=axis2)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        assert SortedList([child1]) == root_node.children
        assert child2 not in root_node.children

    def test_get_root(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "child1"
        axis3.name = "child2"
        grandchild1 = DatacubeRequestTree(axis=axis1)
        child1 = DatacubeRequestTree(axis=axis2)
        child1.add_child(grandchild1)
        child2 = DatacubeRequestTree(axis=axis3)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        root_node.add_child(child2)
        grandparent = grandchild1.get_root()
        assert grandparent == root_node

    def test_merge(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis4 = IntAxis()
        axis5 = IntAxis()
        axis6 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "grandchild2"
        axis3.name = "grandchild3"
        axis4.name = "grandchild4"
        axis5.name = "child1"
        axis6.name = "child2"

        grandchild1_1 = DatacubeRequestTree(axis=axis1)
        grandchild2_1 = DatacubeRequestTree(axis=axis2)
        grandchild3_1 = DatacubeRequestTree(axis=axis3)
        grandchild4_1 = DatacubeRequestTree(axis=axis4)
        child1_1 = DatacubeRequestTree(axis=axis5)
        child1_1.add_child(grandchild1_1)
        child1_1.add_child(grandchild2_1)
        child2_1 = DatacubeRequestTree(axis=axis6)
        child2_1.add_child(grandchild3_1)
        child2_1.add_child(grandchild4_1)
        root_node1 = DatacubeRequestTree()
        root_node1.add_child(child1_1)
        root_node1.add_child(child2_1)
        root_node1.pprint()

        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis4 = IntAxis()
        axis5 = IntAxis()
        axis6 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "grandchild5"
        axis3.name = "grandchild6"
        axis4.name = "grandchild7"
        axis5.name = "child1"
        axis6.name = "child3"

        grandchild1_2 = DatacubeRequestTree(axis=axis1)
        grandchild2_2 = DatacubeRequestTree(axis=axis2)
        grandchild3_2 = DatacubeRequestTree(axis=axis3)
        grandchild4_2 = DatacubeRequestTree(axis=axis4)
        child1_2 = DatacubeRequestTree(axis=axis5)
        child1_2.add_child(grandchild1_2)
        child1_2.add_child(grandchild2_2)
        child2_2 = DatacubeRequestTree(axis=axis6)
        child2_2.add_child(grandchild3_2)
        child2_2.add_child(grandchild4_2)
        root_node2 = DatacubeRequestTree()
        root_node2.add_child(child1_2)
        root_node2.add_child(child2_2)
        root_node2.pprint()

        root_node1.merge(root_node2)
        root_node1.pprint()
        assert len(root_node1.children) == 3
        root_node1.pprint()
        assert set([len(child.children) for child in root_node1.children]) == {2, 2, 3}

    def test_pprint(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "child1"
        axis3.name = "child2"
        grandchild1 = DatacubeRequestTree(axis=axis1)
        child1 = DatacubeRequestTree(axis=axis2)
        child1.add_child(grandchild1)
        child2 = DatacubeRequestTree(axis=axis3)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        root_node.add_child(child2)
        root_node.pprint()

    def test_remove_branch(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "child1"
        axis3.name = "child2"
        grandchild1 = DatacubeRequestTree(axis=axis1)
        child1 = DatacubeRequestTree(axis=axis2)
        child1.add_child(grandchild1)
        child2 = DatacubeRequestTree(axis=axis3)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        root_node.add_child(child2)
        child2.remove_branch()
        assert root_node.children == SortedList([child1])
        assert child1.children == SortedList([grandchild1])
        root_node.add_child(child2)
        child1.remove_branch()
        assert root_node.children == SortedList([child2])

    def test_intersect(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis4 = IntAxis()
        axis5 = IntAxis()
        axis6 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "grandchild2"
        axis3.name = "grandchild3"
        axis4.name = "grandchild4"
        axis5.name = "child1"
        axis6.name = "child2"
        grandchild1_1 = DatacubeRequestTree(axis=axis1)
        grandchild2_1 = DatacubeRequestTree(axis=axis2)
        grandchild3_1 = DatacubeRequestTree(axis=axis3)
        grandchild4_1 = DatacubeRequestTree(axis=axis4)
        child1_1 = DatacubeRequestTree(axis=axis5)
        child1_1.add_child(grandchild1_1)
        child1_1.add_child(grandchild2_1)
        child2_1 = DatacubeRequestTree(axis=axis6)
        child2_1.add_child(grandchild3_1)
        child2_1.add_child(grandchild4_1)
        root_node1 = DatacubeRequestTree()
        root_node1.add_child(child1_1)
        root_node1.add_child(child2_1)

        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis4 = IntAxis()
        axis5 = IntAxis()
        axis6 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "grandchild5"
        axis3.name = "grandchild6"
        axis4.name = "grandchild7"
        axis5.name = "child1"
        axis6.name = "child3"
        grandchild1_2 = DatacubeRequestTree(axis=axis1)
        grandchild2_2 = DatacubeRequestTree(axis=axis2)
        grandchild3_2 = DatacubeRequestTree(axis=axis3)
        grandchild4_2 = DatacubeRequestTree(axis=axis4)
        child1_2 = DatacubeRequestTree(axis=axis5)
        child1_2.add_child(grandchild1_2)
        child1_2.add_child(grandchild2_2)
        child2_2 = DatacubeRequestTree(axis=axis6)
        child2_2.add_child(grandchild3_2)
        child2_2.add_child(grandchild4_2)
        root_node2 = DatacubeRequestTree()
        root_node2.add_child(child1_2)
        root_node2.add_child(child2_2)
        root_node1.pprint()
        root_node2.pprint()

        root_node1.intersect(root_node2)

        root_node1.pprint()
        assert len(root_node1.children) == 1
        assert list(root_node1.children)[0].axis.name == "child1"
        assert len(list(root_node1.children)[0].children) == 1
        assert list(list(root_node1.children)[0].children)[0].axis.name == "grandchild1"

    def test_flatten(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis1.name = "grandchild1"
        axis2.name = "child1"
        axis3.name = "child2"
        grandchild1 = DatacubeRequestTree(axis=axis1)
        child1 = DatacubeRequestTree(axis=axis2)
        child1.add_child(grandchild1)
        child2 = DatacubeRequestTree(axis=axis3)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        root_node.add_child(child2)
        path = grandchild1.flatten()
        assert len(path) == 2
        assert "child1" in path.keys() and "grandchild1" in path.keys()
        assert path["child1"] is None
        assert path["grandchild1"] is None

    def test_get_ancestors(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis1.name = "greatgrandchild1"
        axis2.name = "grandchild1"
        axis3.name = "child1"
        greatgrandchild1 = DatacubeRequestTree(axis=axis1)
        grandchild1 = DatacubeRequestTree(axis=axis2)
        grandchild1.add_child(greatgrandchild1)
        child1 = DatacubeRequestTree(axis=axis3)
        child1.add_child(grandchild1)
        root_node1 = DatacubeRequestTree()
        root_node1.add_child(child1)
        assert greatgrandchild1.get_ancestors() == SortedList([greatgrandchild1, grandchild1, child1])

    def test_add_or_get_child(self):
        axis1 = IntAxis()
        axis1.name = "child1"
        axis2 = IntAxis()
        axis2.name = "child2"
        child1 = DatacubeRequestTree(axis=axis1)
        root_node = DatacubeRequestTree()
        root_node.add_child(child1)
        assert root_node.create_child(axis1, None) == child1
        assert root_node.create_child(axis2, None).parent == root_node

    def test_to_dict(self):
        axis1 = IntAxis()
        axis2 = IntAxis()
        axis3 = IntAxis()
        axis4 = IntAxis()
        axis1.name = "greatgrandchild1"
        axis2.name = "grandchild1"
        axis3.name = "child1"
        axis4.name = "child2"
        greatgrandchild1 = DatacubeRequestTree(axis=axis1)
        greatgrandchild1.result = 1
        grandchild1 = DatacubeRequestTree(axis=axis2)
        grandchild1.add_child(greatgrandchild1)
        child1 = DatacubeRequestTree(axis=axis3)
        child1.add_child(grandchild1)
        child2 = DatacubeRequestTree(axis=axis4)
        root_node1 = DatacubeRequestTree()
        root_node1.add_child(child1)
        root_node1.add_child(child2)
        tree_dict = root_node1.to_dict()
        assert tree_dict == {'child1' :
                             {None :
                              {'grandchild1':
                               {None:
                                {'greatgrandchild1':
                                 {None: 1}
                                 }
                                }
                               }
                              },
                             'child2':
                             {None : None}
                             }
