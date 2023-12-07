import math
from copy import copy
from itertools import chain
from typing import List

import scipy.spatial

from ..datacube.backends.datacube import Datacube, IndexTree
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..shapes import ConvexPolytope
from ..utility.combinatorics import argmax, argmin, group, tensor_product, unique
from ..utility.exceptions import UnsliceableShapeError
from ..utility.geometry import lerp
from .engine import Engine


class HullSlicer(Engine):
    def __init__(self):
        # self.datacube_has_index = {}
        # self.datacube_indices = {}
        # self.sliced_polytopes = {}
        pass

    def _unique_continuous_points(self, p: ConvexPolytope, datacube: Datacube):
        for i, ax in enumerate(p._axes):
            mapper = datacube.get_mapper(ax)
            if isinstance(mapper, UnsliceableDatacubeAxis):
                break
            for j, val in enumerate(p.points):
                p.points[j] = list(p.points[j])
                p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
        # Remove duplicate points
        unique(p.points)

    def _build_unsliceable_child(self, polytope, ax, node, datacube, lower, next_nodes, slice_axis_idx):
        if polytope._axes != [ax.name]:
            raise UnsliceableShapeError(ax)
        path = node.flatten()
        # if (ax.name, lower) not in self.datacube_has_index.keys():
        #     self.datacube_has_index[(ax.name, lower)] = datacube.has_index(path, ax, lower)
        # datacube_has_index_bool = self.datacube_has_index[(ax.name, lower)]
        if datacube.has_index(path, ax, lower):
        # if datacube_has_index_bool:
            child = node.create_child(ax, lower)
            child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            child["unsliced_polytopes"].remove(polytope)
            next_nodes.append(child)
        else:
            # raise a value not found error
            raise ValueError()

    def _build_sliceable_child(self, polytope, ax, node, datacube, lower, upper, next_nodes, slice_axis_idx):
        tol = ax.tol
        lower = ax.from_float(lower - tol)
        upper = ax.from_float(upper + tol)
        # TODO: here we could maybe not flatten the node, since we only need it to find the longitude value in the mappings, instead could look if the node axis is the longitude through the axis mapping options and then only pass that in as a path
        flattened = node.flatten()
        method = polytope.method
        # if (ax, lower, upper, method) not in self.datacube_indices.keys():
        #     self.datacube_indices[(ax, lower, upper, method)] = datacube.get_indices(flattened, ax, lower, upper, method)
        # values = self.datacube_indices[(ax, lower, upper, method)]
        values = datacube.get_indices(flattened, ax, lower, upper, method)

        if len(values) == 0:
            node.remove_branch()

        for value in values:
            # convert to float for slicing
            fvalue = ax.to_float(value)
            # if (polytope, ax.name, fvalue) not in self.sliced_polytopes:
            #     self.sliced_polytopes[(polytope, ax.name, fvalue)] = slice(polytope, ax.name, fvalue, slice_axis_idx)
            # new_polytope = self.sliced_polytopes[(polytope, ax.name, fvalue)]
            new_polytope = slice(polytope, ax.name, fvalue, slice_axis_idx)
            # store the native type
            remapped_val = value
            if ax.is_cyclic:
                remapped_val_interm = ax.remap([value, value])[0]
                remapped_val = (remapped_val_interm[0] + remapped_val_interm[1]) / 2
                remapped_val = round(remapped_val, int(-math.log10(ax.tol)))
            child = node.create_child(ax, remapped_val)
            child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            child["unsliced_polytopes"].remove(polytope)
            if new_polytope is not None:
                child["unsliced_polytopes"].add(new_polytope)
            next_nodes.append(child)

    def _build_tree_layer(self, ax, node, datacube, next_nodes):
        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:
                lower, upper, slice_axis_idx = polytope.extents(ax.name)
                # here, first check if the axis is an unsliceable axis and directly build node if it is
                if isinstance(ax, UnsliceableDatacubeAxis):
                    self._build_unsliceable_child(polytope, ax, node, datacube, lower, next_nodes, slice_axis_idx)
                else:
                    self._build_sliceable_child(polytope, ax, node, datacube, lower, upper, next_nodes, slice_axis_idx)
        del node["unsliced_polytopes"]

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
            self._unique_continuous_points(p, datacube)

        groups, input_axes = group(polytopes)
        datacube.validate(input_axes)
        request = IndexTree()
        combinations = tensor_product(groups)

        # TODO: when would combinations have more than one alternative in the list?
        for c in combinations:
            r = IndexTree()
            r["unsliced_polytopes"] = set(c)
            current_nodes = [r]
            for ax in datacube.axes.values():
                next_nodes = []
                for node in current_nodes:
                    self._build_tree_layer(ax, node, datacube, next_nodes)
                current_nodes = next_nodes
            request.merge(r)
        return request

    def _build_branch(self, ax, node, datacube, next_nodes):
        pass

    def extract_new(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
            self._unique_continuous_points(p, datacube)

        groups, input_axes = group(polytopes)
        datacube.validate(input_axes)
        request = IndexTree()
        combinations = tensor_product(groups)

        for polytope in combinations[0]:
            r = IndexTree()
            r["unsliced_polytopes"] = set([polytope])
            current_nodes = [r]
            r._build_polytope_branch(polytope, datacube, r)

        # for c in combinations:
        #     r = IndexTree()
        #     r["unsliced_polytopes"] = set(c)
        #     current_nodes = [r]
        #     for ax in datacube.axes.values():
        #         next_nodes = []
        #         for node in current_nodes:
        #             self._build_branch(ax, node, datacube, next_nodes)
        #         current_nodes = next_nodes
        #     request.merge(r)
        # return request

    def _build_polytope_branch(self, polytope, datacube, r):
        for ax in polytope._axes:
            lower, upper, slice_axis_idx = polytope.extents(ax)
            axis = datacube.axes[ax]
            if isinstance(ax, UnsliceableDatacubeAxis):
                self._build_unsliceable_sub_child(polytope, axis, r, datacube, lower)
            else:
                self._build_sliceable_sub_branch()

        # for polytope in node["unsliced_polytopes"]:
        #     if ax.name in polytope._axes:
        #         lower, upper, slice_axis_idx = polytope.extents(ax.name)
        #         # here, first check if the axis is an unsliceable axis and directly build node if it is
        #         if isinstance(ax, UnsliceableDatacubeAxis):
        #             self._build_unsliceable_child(polytope, ax, node, datacube, lower, next_nodes, slice_axis_idx)
        #         else:
        #             self._build_sliceable_child(polytope, ax, node, datacube, lower, upper, next_nodes, slice_axis_idx)
        # del node["unsliced_polytopes"]

    def _build_unsliceable_sub_child(self, polytope, ax, node, datacube, lower):
        if polytope._axes != [ax.name]:
            raise UnsliceableShapeError(ax)
        path = node.flatten()
        if (ax.name, lower) not in self.datacube_has_index.keys():
            self.datacube_has_index[(ax.name, lower)] = datacube.has_index(path, ax, lower)
        datacube_has_index_bool = self.datacube_has_index[(ax.name, lower)]
        if datacube_has_index_bool:
            child = node.create_child(ax, lower)
        else:
            raise ValueError()


def _find_intersects(polytope, slice_axis_idx, value):
    intersects = []
    # Find all points above and below slice axis
    above_slice = [p for p in polytope.points if p[slice_axis_idx] >= value]
    below_slice = [p for p in polytope.points if p[slice_axis_idx] <= value]

    # Get the intersection of every pair above and below, this will create excess interior points
    for a in above_slice:
        for b in below_slice:
            # edge is incident with slice plane, don't need these points
            if a[slice_axis_idx] == b[slice_axis_idx]:
                intersects.append(b)
                continue

            # Linearly interpolate all coordinates of two points (a,b) of the polytope
            interp_coeff = (value - b[slice_axis_idx]) / (a[slice_axis_idx] - b[slice_axis_idx])
            intersect = lerp(a, b, interp_coeff)
            intersects.append(intersect)
    return intersects


def _reduce_dimension(intersects, slice_axis_idx):
    temp_intersects = []
    for point in intersects:
        point = [p for i, p in enumerate(point) if i != slice_axis_idx]
        temp_intersects.append(point)
    return temp_intersects


def slice(polytope: ConvexPolytope, axis, value, slice_axis_idx):
    if len(polytope.points[0]) == 1:
        # Note that in this case, we do not need to do linear interpolation so we can save time
        if value in chain(*polytope.points):
            intersects = [[value]]
        else:
            return None
    else:
        intersects = _find_intersects(polytope, slice_axis_idx, value)

    if len(intersects) == 0:
        return None

    # Reduce dimension of intersection points, removing slice axis
    intersects = _reduce_dimension(intersects, slice_axis_idx)

    axes = [ax for ax in polytope._axes if ax != axis]

    if len(intersects) < len(intersects[0]) + 1:
        return ConvexPolytope(axes, intersects)
    # Compute convex hull (removing interior points)
    if len(intersects[0]) == 0:
        return None
    elif len(intersects[0]) == 1:  # qhull doesn't like 1D, do it ourselves
        amin = argmin(intersects)
        amax = argmax(intersects)
        vertices = [amin, amax]
    else:
        try:
            hull = scipy.spatial.ConvexHull(intersects)
            vertices = hull.vertices

        except scipy.spatial.qhull.QhullError as e:
            if "less than" or "flat" in str(e):
                return ConvexPolytope(axes, intersects)
    # Sliced result is simply the convex hull
    return ConvexPolytope(axes, [intersects[i] for i in vertices])
