from copy import copy
from itertools import chain
from typing import List

import scipy.spatial

from ..datacube.datacube import Datacube, DatacubeRequestTree
from ..datacube.datacube_axis import UnsliceableaAxis
from ..shapes import ConvexPolytope
from ..utility.combinatorics import argmax, argmin, group, product, unique
from ..utility.exceptions import UnsliceableShapeError
from ..utility.geometry import lerp
from .engine import Engine


class HullSlicer(Engine):
    def __init__(self):
        pass

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        # Convert the polytope points to float type to support triangulation and interpolation

        for p in polytopes:
            for i, ax in enumerate(p.axes()):
                mapper = datacube.get_mapper(ax)
                if isinstance(mapper, UnsliceableaAxis):
                    break
                for j, val in enumerate(p.points):
                    p.points[j] = list(p.points[j])
                    p.points[j][i] = mapper.to_float(mapper.parse(p.points[j][i]))

            # Remove duplicate points
            unique(p.points)

        groups, input_axes = group(polytopes)

        datacube.validate(input_axes)

        request = DatacubeRequestTree()
        combinations = product(groups)

        # TODO: maybe use generators here?

        for c in combinations:
            r = DatacubeRequestTree()
            r["unsliced_polytopes"] = set(c)
            current_nodes = [r]
            for axis_name, ax in datacube.axes.items():
                next_nodes = []
                for node in current_nodes:
                    for polytope in node["unsliced_polytopes"]:
                        if axis_name in polytope.axes():
                            lower, upper = polytope.extents(axis_name)

                            # here, first check if the axis is an unsliceable axis and directly build node if it is
                            if isinstance(ax, UnsliceableaAxis):
                                if polytope.axes() != [ax.name]:
                                    raise UnsliceableShapeError(ax)
                                path = node.flatten()
                                if datacube.has_index(path, ax, lower):
                                    child = node.create_child(ax, lower)
                                    child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
                                    child["unsliced_polytopes"].remove(polytope)
                                    next_nodes.append(child)
                                else:
                                    # raise a value not found error
                                    raise ValueError()
                            else:
                                # convert to native type to discretize on datacube
                                tol = ax.tol
                                lower = ax.from_float(lower - tol)
                                upper = ax.from_float(upper + tol)
                                flattened = node.flatten()
                                for value in datacube.get_indices(flattened, ax, lower, upper):
                                    # convert to float for slicing
                                    fvalue = ax.to_float(value)
                                    new_polytope = slice(polytope, axis_name, fvalue)
                                    # store the native type
                                    child = node.create_child(ax, value)
                                    child["unsliced_polytopes"] = copy(node["unsliced_polytopes"])
                                    child["unsliced_polytopes"].remove(polytope)
                                    if new_polytope is not None:
                                        child["unsliced_polytopes"].add(new_polytope)
                                    next_nodes.append(child)
                    del node["unsliced_polytopes"]
                current_nodes = next_nodes

            request.merge(r)

        return request


def slice(polytope: ConvexPolytope, axis, value):
    slice_axis_idx = polytope._axes.index(axis)

    if len(polytope.points[0]) == 1:
        # Note that in this case, we do not need to do linear interpolation so we can save time
        if value in chain(*polytope.points):
            intersects = [[value]]
        else:
            return None

    # TODO: shortcut if number of points in polytope == 2 (and maybe some other trivial situations)
    # TODO: if the polytope only has two dimensions/axis, maybe simplify?

    else:
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

    if len(intersects) == 0:
        return None

    # Reduce dimension of intersection points, removing slice axis

    # TODO: refactor this more efficiently
    temp_intersects = []
    for point in intersects:
        point = [p for i, p in enumerate(point) if i != slice_axis_idx]
        temp_intersects.append(point)
    intersects = temp_intersects

    axes = [ax for ax in polytope.axes() if ax != axis]

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
            if "input is less than" or "simplex is flat" in str(e):
                return ConvexPolytope(axes, intersects)

    # Sliced result is simply the convex hull
    return ConvexPolytope(axes, [intersects[i] for i in vertices])


# To profile, put @profile in front of slice and then do: kernprof -l -v tests/test_hull_slicer.py in terminal
