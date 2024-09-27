import math
from copy import copy
from itertools import chain
from typing import List

import scipy.spatial

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
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
        self.compressed_axes = []

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

    def _build_unsliceable_child(self, polytope, ax, node, datacube, lowers, next_nodes, slice_axis_idx):
        if not polytope.is_flat:
            raise UnsliceableShapeError(ax)
        path = node.flatten()

        # all unsliceable children are natively 1D so can group them together in a tuple...
        flattened_tuple = tuple()
        if len(datacube.coupled_axes) > 0:
            if path.get(datacube.coupled_axes[0][0], None) is not None:
                flattened_tuple = (datacube.coupled_axes[0][0], path.get(datacube.coupled_axes[0][0], None))
                path = {flattened_tuple[0]: flattened_tuple[1]}

        for i, lower in enumerate(lowers):
            if self.axis_values_between.get((flattened_tuple, ax.name, lower), None) is None:
                self.axis_values_between[(flattened_tuple, ax.name, lower)] = datacube.has_index(path, ax, lower)
            datacube_has_index = self.axis_values_between[(flattened_tuple, ax.name, lower)]

            if datacube_has_index:
                if i == 0:
                    (child, next_nodes) = node.create_child(ax, lower, next_nodes)
                    child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
                    child["unsliced_polytopes"].remove(polytope)
                    next_nodes.append(child)
                else:
                    child.add_value(lower)
            else:
                # raise a value not found error
                errmsg = (
                    f"Datacube does not have expected index {lower} of type {type(lower)}"
                    f"on {ax.name} along the path {path}"
                )
                raise ValueError(errmsg)

    def find_values_between(self, polytope, ax, node, datacube, lower, upper):
        tol = ax.tol
        lower = ax.from_float(lower - tol)
        upper = ax.from_float(upper + tol)
        flattened = node.flatten()
        method = polytope.method
        if method == "nearest":
            datacube.nearest_search[ax.name] = polytope.points

        # NOTE: caching
        # Create a coupled_axes list inside of datacube and add to it during axis formation, then here
        # do something like if ax is in second place of coupled_axes, then take the flattened part of the array that
        # corresponds to the first place of cooupled_axes in the hashing
        # Else, if we do not need the flattened bit in the hash, can just put an empty string instead?

        flattened_tuple = tuple()
        if len(datacube.coupled_axes) > 0:
            if flattened.get(datacube.coupled_axes[0][0], None) is not None:
                flattened_tuple = (datacube.coupled_axes[0][0], flattened.get(datacube.coupled_axes[0][0], None))
                flattened = {flattened_tuple[0]: flattened_tuple[1]}

        values = self.axis_values_between.get((flattened_tuple, ax.name, lower, upper, method), None)
        if values is None:
            values = datacube.get_indices(flattened, ax, lower, upper, method)
            self.axis_values_between[(flattened_tuple, ax.name, lower, upper, method)] = values
        return values

    def remap_values(self, ax, value):
        remapped_val = self.remapped_vals.get((value, ax.name), None)
        if remapped_val is None:
            remapped_val = value
            if ax.is_cyclic:
                remapped_val_interm = ax.remap([value, value])[0]
                remapped_val = (remapped_val_interm[0] + remapped_val_interm[1]) / 2
            if ax.can_round:
                remapped_val = round(remapped_val, int(-math.log10(ax.tol)))
            self.remapped_vals[(value, ax.name)] = remapped_val
        return remapped_val

    def _build_sliceable_child(self, polytope, ax, node, datacube, values, next_nodes, slice_axis_idx):
        for i, value in enumerate(values):
            if i == 0 or ax.name not in self.compressed_axes:
                fvalue = ax.to_float(value)
                new_polytope = slice(polytope, ax.name, fvalue, slice_axis_idx)
                remapped_val = self.remap_values(ax, value)
                (child, next_nodes) = node.create_child(ax, remapped_val, next_nodes)
                child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
                child["unsliced_polytopes"].remove(polytope)
                if new_polytope is not None:
                    child["unsliced_polytopes"].add(new_polytope)
                next_nodes.append(child)
            else:
                remapped_val = self.remap_values(ax, value)
                child.add_value(remapped_val)

    def _build_branch(self, ax, node, datacube, next_nodes):
        if ax.name not in self.compressed_axes:
            parent_node = node.parent
            right_unsliced_polytopes = []
            for polytope in node["unsliced_polytopes"]:
                if ax.name in polytope._axes:
                    right_unsliced_polytopes.append(polytope)
            for i, polytope in enumerate(right_unsliced_polytopes):
                node._parent = parent_node
                lower, upper, slice_axis_idx = polytope.extents(ax.name)
                # here, first check if the axis is an unsliceable axis and directly build node if it is
                # NOTE: we should have already created the ax_is_unsliceable cache before
                if self.ax_is_unsliceable[ax.name]:
                    self._build_unsliceable_child(polytope, ax, node, datacube, [lower], next_nodes, slice_axis_idx)
                else:
                    values = self.find_values_between(polytope, ax, node, datacube, lower, upper)
                    # NOTE: need to only remove the branches if the values are empty,
                    # but only if there are no other possible children left in the tree that
                    # we can append and if somehow this happens before and we need to remove, then what do we do??
                    if i == len(right_unsliced_polytopes) - 1:
                        # we have iterated all polytopes and we can now remove the node if we need to
                        if len(values) == 0 and len(node.children) == 0:
                            node.remove_branch()
                    self._build_sliceable_child(polytope, ax, node, datacube, values, next_nodes, slice_axis_idx)
        else:
            all_values = []
            all_lowers = []
            first_polytope = False
            first_slice_axis_idx = False
            parent_node = node.parent
            for polytope in node["unsliced_polytopes"]:
                node._parent = parent_node
                if ax.name in polytope._axes:
                    # keep track of the first polytope defined on the given axis
                    if not first_polytope:
                        first_polytope = polytope
                    lower, upper, slice_axis_idx = polytope.extents(ax.name)
                    if not first_slice_axis_idx:
                        first_slice_axis_idx = slice_axis_idx
                    if self.ax_is_unsliceable[ax.name]:
                        all_lowers.append(lower)
                    else:
                        values = self.find_values_between(polytope, ax, node, datacube, lower, upper)
                        all_values.extend(values)
            if self.ax_is_unsliceable[ax.name]:
                self._build_unsliceable_child(
                    first_polytope, ax, node, datacube, all_lowers, next_nodes, first_slice_axis_idx
                )
            else:
                if len(all_values) == 0:
                    node.remove_branch()
                self._build_sliceable_child(
                    first_polytope, ax, node, datacube, all_values, next_nodes, first_slice_axis_idx
                )

        del node["unsliced_polytopes"]

    def find_compressed_axes(self, datacube, polytopes):
        # First determine compressable axes from input polytopes
        compressable_axes = []
        for polytope in polytopes:
            if polytope.is_orthogonal:
                for ax in polytope.axes():
                    compressable_axes.append(ax)
        # Cross check this list with list of compressable axis from datacube
        # (should not include any merged or coupled axes)
        for compressed_axis in compressable_axes:
            if compressed_axis in datacube.compressed_axes:
                self.compressed_axes.append(compressed_axis)
        # add the last axis of the grid always (longitude) as a compressed axis
        k, last_value = _, datacube.axes[k] = datacube.axes.popitem()
        self.compressed_axes.append(k)

    def remove_compressed_axis_in_union(self, polytopes):
        for p in polytopes:
            if p.is_in_union:
                for axis in p.axes():
                    if axis == self.compressed_axes[-1]:
                        self.compressed_axes.remove(axis)

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        # Determine list of axes to compress
        self.find_compressed_axes(datacube, polytopes)

        # remove compressed axes which are in a union
        self.remove_compressed_axis_in_union(polytopes)

        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
            self._unique_continuous_points(p, datacube)

        groups, input_axes = group(polytopes)
        datacube.validate(input_axes)
        request = TensorIndexTree()
        combinations = tensor_product(groups)

        # NOTE: could optimise here if we know combinations will always be for one request.
        # Then we do not need to create a new index tree and merge it to request, but can just
        # directly work on request and return it...

        for c in combinations:
            r = TensorIndexTree()
            new_c = []
            for combi in c:
                if isinstance(combi, list):
                    new_c.extend(combi)
                else:
                    new_c.append(combi)
            r["unsliced_polytopes"] = set(new_c)
            current_nodes = [r]
            for ax in datacube.axes.values():
                next_nodes = []
                interm_next_nodes = []
                for node in current_nodes:
                    self._build_branch(ax, node, datacube, interm_next_nodes)
                    next_nodes.extend(interm_next_nodes)
                    interm_next_nodes = []
                current_nodes = next_nodes

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
