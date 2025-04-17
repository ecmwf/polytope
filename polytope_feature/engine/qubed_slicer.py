
import math
from copy import copy
from itertools import chain
from typing import List

import scipy.spatial

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope, Product
from ..utility.combinatorics import group, tensor_product
from ..utility.exceptions import UnsliceableShapeError
from ..utility.geometry import lerp
from ..utility.list_tools import argmax, argmin, unique
from .engine import Engine

from qubed import Qube
from qubed.value_types import QEnum
from typing import Iterator
from ...engine.hullslicer import slice
from copy import deepcopy
import pandas as pd
from ..datacube_axis import UnsliceableDatacubeAxis


class QubedSlicer(Engine):
    def __init__(self):
        self.ax_is_unsliceable = {}
        self.axis_values_between = {}
        self.has_value = {}
        self.sliced_polytopes = {}
        self.remapped_vals = {}
        self.compressed_axes = []

    # TODO: assert that the associated datacube is an FDB one

    # TODO: change functions to reuse same methods as other slicers

    # TODO: get the transformations + datacube axes from the datacube now

    # TODO: separate the extract into the combinations and then do the slicing for each combination

    def find_polytope_combinations(self):
        pass

    def actual_slice(q: Qube, polytopes_to_slice, datacube_axes, datacube_transformations) -> 'Qube':
        # TODO: when there is a qubed leaf, make sure to add/consider the mapper grid axes too

        def find_polytopes_on_axis(q: Qube, polytopes):
            polytopes_on_axis = []
            axis_name = q.key
            for poly in polytopes:
                if axis_name in poly._axes:
                    polytopes_on_axis.append(poly)
            return polytopes_on_axis

        def change_poly_axis_type(axis_name, polytopes, datacube_axes):
            axis = datacube_axes[axis_name]
            # TODO: loop through the polytopes and change each polytopes's values according to axis
            if isinstance(axis, UnsliceableDatacubeAxis):
                return

            for poly in polytopes:
                i = 0
                for k, ax_name in enumerate(poly._axes):
                    if ax_name == axis_name:
                        i = k
                for j, val in enumerate(poly.points):
                    poly.points[j][i] = axis.to_float(axis.parse(poly.points[j][i]))

        def _axes_compressed():
            return {}

        def change_datacube_val_types(child: Qube, datacube_transformations):
            axis_name = child.key
            transformation = datacube_transformations.get(axis_name, None)
            child_vals = child.values
            new_vals = []
            for val in child_vals:
                if transformation:
                    new_vals.append(transformation.transform_type(val))
                else:
                    new_vals.append(val)

            return new_vals

        def transform_upper_lower(axis_name, lower, upper, datacube_axes):
            ax = datacube_axes[axis_name]
            if isinstance(ax, UnsliceableDatacubeAxis):
                return (lower, upper)
            tol = ax.tol
            lower = ax.from_float(lower - tol)
            upper = ax.from_float(upper + tol)

            return (lower, upper)

        def _slice(q: Qube, polytopes, datacube_axes, datacube_transformations) -> list[Qube]:
            result = []
            for child in q.children:
                # find polytopes which are defined on axis child.key
                polytopes_on_axis = find_polytopes_on_axis(child, polytopes)

                # here now first change the values in the polytopes on the axis to reflect the axis type

                # for each polytope:
                for poly in polytopes_on_axis:
                    # find extents of polytope on child.key
                    lower, upper, slice_axis_idx = poly.extents(child.key)
                    # find values on child that are within extents
                    # here first change the child values of the datacube ie the Qubed tree to their right type with the transformation
                    modified_vals = change_datacube_val_types(child, datacube_transformations)

                    # here use the axis to transform lower and upper to right type too
                    new_lower, new_upper = transform_upper_lower(child.key, lower, upper, datacube_axes)
                    found_vals = [v for v in modified_vals if new_lower <= v <= new_upper]

                    if len(found_vals) == 0:
                        continue

                    # slice polytope along each value on child and keep resulting polytopes in memory
                    sliced_polys = []
                    for val in found_vals:
                        ax = datacube_axes[child.key]
                        if not isinstance(ax, UnsliceableDatacubeAxis):
                            fval = ax.to_float(val)
                            # slice polytope along the value and add sliced polytope to list of polytopes in memory
                            sliced_poly = slice(poly, child.key, fval, slice_axis_idx)
                            sliced_polys.append(sliced_poly)

                    # decide if axis should be compressed or not according to polytope
                    axis_compressed = _axes_compressed().get(child.key, False)
                    # if it's not compressed, need to separate into different nodes to append to the tree
                    if not axis_compressed and len(found_vals) > 1:
                        polytopes.remove(poly)
                        for i, found_val in enumerate(found_vals):
                            # TODO: before removing polytope here actually, we should be careful that all the values in the polytope are on this branch... so we can't just remove here in theory
                            child_polytopes = deepcopy(polytopes)
                            if sliced_polys[i]:
                                child_polytopes.append(sliced_polys[i])
                            children = _slice(child, child_polytopes, datacube_axes, datacube_transformations)
                            # If this node used to have children but now has none due to filtering, skip it.
                            if child.children and not children:
                                continue
                            # TODO: add the child_polytopes to the child.metadata/ ie change child.metadata here before passing?
                            if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                                found_val = [str(found_val)]
                            qube_node = Qube.make(key=child.key,
                                                  values=QEnum(found_val),
                                                  metadata=child.metadata,
                                                  children=children)
                            result.append(qube_node)
                    else:
                        # if it's compressed, then can add all found values in a single node
                        polytopes.remove(poly)
                        child_polytopes = deepcopy(polytopes)
                        child_polytopes.extend(
                            [sliced_poly_ for sliced_poly_ in sliced_polys if sliced_poly_ is not None])
                        # create children
                        children = _slice(child, child_polytopes, datacube_axes, datacube_transformations)
                        # If this node used to have children but now has none due to filtering, skip it.
                        if child.children and not children:
                            continue

                        # TODO: add the child_polytopes to the child.metadata/ ie change child.metadata here before passing
                        result.extend([Qube.make(
                            key=child.key,
                            values=QEnum(found_vals),
                            metadata=child.metadata,
                            children=children
                        )])

            return result

        # change the polytope point types here
        for polytope in polytopes_to_slice:
            for axis in polytope._axes:
                change_poly_axis_type(axis, [polytope], datacube_axes)

        return Qube.root_node(_slice(q, polytopes_to_slice, datacube_axes, datacube_transformations))
