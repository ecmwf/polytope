from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope
from .combinatorics import group, tensor_product, unique


def unique_continuous_points_in_polytope(p: ConvexPolytope, datacube: Datacube):
    # TODO: should this be in utility folder since it doesn't really depend on engine...?
    for i, ax in enumerate(p._axes):
        mapper = datacube.get_mapper(ax)
        if isinstance(mapper, UnsliceableDatacubeAxis):
            break
        for j, val in enumerate(p.points):
            p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
    # Remove duplicate points
    unique(p.points)


def find_polytope_combinations(datacube: Datacube, polytopes: List[ConvexPolytope]) -> TensorIndexTree:
    # here, we find the different possible polytope combinations that cover all of the datacube axes

    for p in polytopes:
        unique_continuous_points_in_polytope(p, datacube)

    groups, input_axes = group(polytopes)
    datacube.validate(input_axes)
    combinations = tensor_product(groups)
    return combinations
