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
        self.ax_is_unsliceable = {}
        self.axis_values_between = {}
        self.has_value = {}
        self.sliced_polytopes = {}
        self.remapped_vals = {}

    def _unique_continuous_points(self, p: ConvexPolytope, datacube: Datacube):
        for i, ax in enumerate(p._axes):
            mapper = datacube.get_mapper(ax)
            if self.ax_is_unsliceable.get(ax, None) is None:
                self.ax_is_unsliceable[ax] = isinstance(mapper, UnsliceableDatacubeAxis)
            if self.ax_is_unsliceable[ax]:
                break
            for j, val in enumerate(p.points):
                p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))
        # Remove duplicate points
        unique(p.points)

    def _build_unsliceable_child(self, polytope, ax, node, datacube, lower, next_nodes, slice_axis_idx):
        if not polytope.is_flat:
            raise UnsliceableShapeError(ax)
        path = node.flatten()

        flattened_tuple = tuple()
        if len(datacube.coupled_axes) > 0:
            if path.get(datacube.coupled_axes[0][0], None) is not None:
                flattened_tuple = (datacube.coupled_axes[0][0], path.get(datacube.coupled_axes[0][0], None))
                path = {flattened_tuple[0]: flattened_tuple[1]}
            else:
                path = {}

        if self.axis_values_between.get((flattened_tuple, ax.name, lower), None) is None:
            self.axis_values_between[(flattened_tuple, ax.name, lower)] = datacube.has_index(path, ax, lower)
        datacube_has_index = self.axis_values_between[(flattened_tuple, ax.name, lower)]

        if datacube_has_index:
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
        flattened = node.flatten()
        method = polytope.method
        if method == "nearest":
            datacube.nearest_search[ax.name] = polytope.points

        # TODO: this hashing doesn't work because we need to know the latitude val for finding longitude values
        # TODO: Maybe create a coupled_axes list inside of datacube and add to it during axis formation, then here
        # do something like if ax is in second place of coupled_axes, then take the flattened part of the array that
        # corresponds to the first place of cooupled_axes in the hashing
        # Else, if we do not need the flattened bit in the hash, can just put an empty string instead?

        flattened_tuple = tuple()
        if len(datacube.coupled_axes) > 0:
            if flattened.get(datacube.coupled_axes[0][0], None) is not None:
                flattened_tuple = (datacube.coupled_axes[0][0], flattened.get(datacube.coupled_axes[0][0], None))
                flattened = {flattened_tuple[0]: flattened_tuple[1]}
            else:
                flattened = {}

        values = self.axis_values_between.get((flattened_tuple, ax.name, lower, upper, method), None)
        if self.axis_values_between.get((flattened_tuple, ax.name, lower, upper, method), None) is None:
            values = datacube.get_indices(flattened, ax, lower, upper, method)
            self.axis_values_between[(flattened_tuple, ax.name, lower, upper, method)] = values

        if len(values) == 0:
            node.remove_branch()

        for value in values:
            # convert to float for slicing
            fvalue = ax.to_float(value)
            new_polytope = self.sliced_polytopes.get((polytope, ax.name, fvalue, slice_axis_idx), False)
            if new_polytope is False:
                new_polytope = slice(polytope, ax.name, fvalue, slice_axis_idx)
                self.sliced_polytopes[(polytope, ax.name, fvalue, slice_axis_idx)] = new_polytope

            # store the native type
            remapped_val = self.remapped_vals.get((value, ax.name), None)
            if remapped_val is None:
                remapped_val = value
                if ax.is_cyclic:
                    remapped_val_interm = ax.remap([value, value])[0]
                    remapped_val = (remapped_val_interm[0] + remapped_val_interm[1]) / 2
                    remapped_val = round(remapped_val, int(-math.log10(ax.tol)))
                self.remapped_vals[(value, ax.name)] = remapped_val

            child = node.create_child(ax, remapped_val)
            child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
            child["unsliced_polytopes"].remove(polytope)
            if new_polytope is not None:
                child["unsliced_polytopes"].add(new_polytope)
            next_nodes.append(child)

    def _build_branch(self, ax, node, datacube, next_nodes):
        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:
                lower, upper, slice_axis_idx = polytope.extents(ax.name)
                # here, first check if the axis is an unsliceable axis and directly build node if it is

                # NOTE: we should have already created the ax_is_unsliceable cache before

                if self.ax_is_unsliceable[ax.name]:
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

        # NOTE: could optimise here if we know combinations will always be for one request.
        # Then we do not need to create a new index tree and merge it to request, but can just
        # directly work on request and return it...

        for c in combinations:
            cached_node = None
            repeated_sub_nodes = []

            r = IndexTree()
            r["unsliced_polytopes"] = set(c)
            current_nodes = [r]
            for ax in datacube.axes.values():
                next_nodes = []
                for node in current_nodes:
                    # detect if node is for number == 1
                    # store a reference to that node
                    # skip processing the other 49 numbers
                    # at the end, copy that initial reference 49 times and add to request with correct number

                    stored_val = None
                    if node.axis.name == datacube.axis_with_identical_structure_after:
                        stored_val = node.value
                        cached_node = node
                        # logging.info("Caching number 1")
                    elif node.axis.name == datacube.axis_with_identical_structure_after and node.value != stored_val:
                        repeated_sub_nodes.append(node)
                        del node["unsliced_polytopes"]
                        # logging.info(f"Skipping number {node.value}")
                        continue

                    self._build_branch(ax, node, datacube, next_nodes)
                current_nodes = next_nodes

            # logging.info("=== BEFORE COPYING ===")

            for n in repeated_sub_nodes:
                # logging.info(f"Copying children for number {n.value}")
                n.copy_children_from_other(cached_node)

            # logging.info("=== AFTER COPYING ===")
            # request.pprint()

            request.merge(r)
        return request


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
    if polytope.is_flat:
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

    axes = copy(polytope._axes)
    axes.remove(axis)

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
