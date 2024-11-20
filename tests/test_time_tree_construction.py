import time

from polytope_feature.datacube.tensor_index_tree import TensorIndexTree
from polytope_feature.datacube.datacube_axis import IntDatacubeAxis


root = TensorIndexTree()
axis1 = IntDatacubeAxis()
axis2 = IntDatacubeAxis()
axis3 = IntDatacubeAxis()

time0 = time.time()
for i in range(100):
    child = TensorIndexTree(axis1, (0,))
    for j in range(100):
        gchild = TensorIndexTree(axis2, (0,))
        for k in range(1000):
            ggchild = TensorIndexTree(axis3, (0,))
            gchild.add_child(ggchild)
        child.add_child(gchild)
    root.add_child(child)
time1 = time.time()
print(time1 - time0)
