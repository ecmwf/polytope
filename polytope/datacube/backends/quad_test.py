# TODO: create quadtree from a set of 2D points with each leaf containing exactly one data point
from .datacube import Datacube

# import quads

# tree = quads.QuadTree((0, 0), 360, 180)
# tree.insert((0, 0))
# tree.insert((90, 0))
# tree.insert((90, 40))
# tree.insert((60, 10))
# a = tree.find((1, 2))
# # quads.visualize(tree)

# import scipy.spatial as scsp
# from copy import deepcopy

# new_tree = scsp.KDTree([[0, 0], [90, 0], [90, 40], [60, 10]])

# import numpy as np
# from scipy.spatial import KDTree
# import matplotlib.pyplot as plt

# x, y = np.mgrid[0:5, 0:8]
# tree = KDTree(np.c_[x.ravel(), y.ravel()])
# plt.plot(x, y, marker='o', color='k', linestyle='none')
# # plt.show()

# dd, ii = tree.query([[1.501, 2.5]], k=2)
# print(dd, ii, sep='\n')
# print("nearest point")
# print(np.c_[x.ravel(), y.ravel()][ii])

# print("\n")
# print(tree.maxes)
# print(tree.mins)
# print(tree.leafsize)
# print(tree.tree)
# print(tree.n)


class IrregularGridDatacube(Datacube):

    def __init__(self, points, config={}, axis_options={}):
        self.points = points

    def lat_points(self):
        return [p[0] for p in self.points]

    def lon_points(self):
        return [p[1] for p in self.points]
