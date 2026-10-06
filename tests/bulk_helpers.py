from polytope_feature.datacube.tensor_index_tree import BulkMergedTensorIndexNode


class PointLeaf:
    """One point of a bulk leaf, exposing the interface of a legacy one-point leaf."""

    def __init__(self, bulk_node, i):
        self.bulk_node = bulk_node
        self.i = i

    @property
    def indexes(self):
        return [int(self.bulk_node.indexes[self.i])]

    @property
    def tags(self):
        return self.bulk_node.point_tags[self.i]

    @property
    def result(self):
        return [values[self.i] for values in self.bulk_node.result]

    def flatten(self):
        path = self.bulk_node.parent.flatten()
        lat, lon = self.bulk_node.coordinates[self.i]
        path[self.bulk_node.axes[0].name] = [float(lat)]
        path[self.bulk_node.axes[1].name] = [float(lon)]
        return path


def point_leaves(tree):
    """Return the leaves of ``tree``, with every bulk leaf expanded into one PointLeaf per point."""
    leaves = []
    for leaf in tree.leaves:
        if isinstance(leaf, BulkMergedTensorIndexNode):
            leaves.extend(PointLeaf(leaf, i) for i in range(leaf.point_count))
        else:
            leaves.append(leaf)
    return leaves
