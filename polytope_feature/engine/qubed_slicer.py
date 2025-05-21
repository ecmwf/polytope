
from qubed import Qube
from qubed.value_types import QEnum
from qubed.set_operations import union
from .hullslicer import slice
from ..datacube.backends.qubed import QubedDatacube
from .engine import Engine
import pandas as pd
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.transformations.datacube_mappers.datacube_mappers import DatacubeMapper
from ..shapes import ConvexPolytope, Product
from ..utility.combinatorics import group, tensor_product
from typing import List

from ..datacube.backends.datacube import Datacube
import math


class QubedSlicer(Engine):
    def __init__(self):
        self.ax_is_unsliceable = {}
        self.compressed_axes = []
        self.remapped_vals = {}

    def find_datacube_vals():
        # TODO
        pass

    def find_values_between(self, polytope, ax, node, datacube, lower, upper, path=None):
        if isinstance(ax, UnsliceableDatacubeAxis):
            return [v for v in node.values if lower <= v <= upper]

        tol = ax.tol
        lower = ax.from_float(lower - tol)
        upper = ax.from_float(upper + tol)

        method = polytope.method

        # values = datacube.get_indices(flattened, ax, lower, upper, method)
        values = datacube.get_indices(path, node, ax, lower, upper, method)
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

    def _actual_slice(self, q: Qube, polytopes_to_slice, datacube, datacube_transformations) -> 'Qube':

        def find_polytopes_on_axis(axis_name, polytopes):
            polytopes_on_axis = []
            for poly in polytopes:
                if axis_name in poly._axes:
                    polytopes_on_axis.append(poly)
            return polytopes_on_axis

        def change_datacube_val_types(child: Qube, datacube_transformations):
            axis_name = child.key
            transformation = datacube_transformations.get(axis_name, None)
            child_vals = child.values

            # TODO: use axis.find_indexes_between to find the right child_vals
            # TODO: actually, build same as find_values_between(self, polytope, ax, node, datacube, lower, upper) by writing new functions in qubed backend
            new_vals = []
            for val in child_vals:
                if transformation:
                    new_vals.append(transformation.transform_type(val))
                else:
                    new_vals.append(val)

            return new_vals

        def transform_upper_lower(axis_name, lower, upper, datacube):
            ax = datacube._axes[axis_name]
            if isinstance(ax, UnsliceableDatacubeAxis):
                return (lower, upper)
            tol = ax.tol
            lower = ax.from_float(lower - tol)
            upper = ax.from_float(upper + tol)

            return (lower, upper)

        def _slice_second_grid_axis(axis_name, polytopes, datacube, datacube_transformations, second_axis_vals, path) -> list[Qube]:
            result = []
            polytopes_on_axis = find_polytopes_on_axis(axis_name, polytopes)

            for poly in polytopes_on_axis:
                ax = datacube._axes[axis_name]
                lower, upper, slice_axis_idx = poly.extents(axis_name)

                # new_lower, new_upper = transform_upper_lower(axis_name, lower, upper, datacube)
                # found_vals = [v for v in second_axis_vals if new_lower <= v <= new_upper]
                found_vals = self.find_values_between(poly, ax, None, datacube, lower, upper, path)

                if len(found_vals) == 0:
                    continue

                # slice polytope along each value on child and keep resulting polytopes in memory
                sliced_polys = []
                for val in found_vals:
                    # ax = datacube._axes[axis_name]
                    if not isinstance(ax, UnsliceableDatacubeAxis):
                        fval = ax.to_float(val)
                        # slice polytope along the value and add sliced polytope to list of polytopes in memory
                        sliced_poly = slice(poly, axis_name, fval, slice_axis_idx)
                        sliced_polys.append(sliced_poly)
                # decide if axis should be compressed or not according to polytope
                # NOTE: actually the second grid axis will always be compressed

                # if it's not compressed, need to separate into different nodes to append to the tree

                new_found_vals = []
                for found_val in found_vals:
                    found_val = self.remap_values(ax, found_val)
                    if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                        new_found_vals.append(str(found_val))
                    else:
                        new_found_vals.append(found_val)

                # NOTE this was the last axis so we do not have children...

                result.extend([Qube.make(
                    key=axis_name,
                    values=QEnum(new_found_vals),
                    metadata={},
                    children={}
                )])
            return result

        def _slice(q: Qube, polytopes, datacube, datacube_transformations) -> list[Qube]:
            result = []

            if len(q.children) == 0:
                # add "fake" axes and their nodes in order -> what about merged axes??
                mapper_transformation = None
                for transformation in list(datacube_transformations.values()):
                    if isinstance(transformation, DatacubeMapper):
                        mapper_transformation = transformation
                if not mapper_transformation:
                    # There is no grid mapping
                    pass
                else:
                    # Slice on the two grid axes
                    grid_axes = mapper_transformation._mapped_axes

                    # Handle first grid axis
                    polytopes_on_axis = find_polytopes_on_axis(grid_axes[0], polytopes)

                    for poly in polytopes_on_axis:
                        ax = datacube._axes[grid_axes[0]]
                        lower, upper, slice_axis_idx = poly.extents(grid_axes[0])

                        first_ax_vals = mapper_transformation.first_axis_vals()

                        # new_lower, new_upper = transform_upper_lower(grid_axes[0], lower, upper, datacube)
                        # found_vals = [v for v in first_ax_vals if new_lower <= v <= new_upper]
                        found_vals = self.find_values_between(poly, ax, None, datacube, lower, upper)

                        if len(found_vals) == 0:
                            continue

                        # slice polytope along each value on child and keep resulting polytopes in memory
                        sliced_polys = []
                        for val in found_vals:
                            # ax = datacube._axes[grid_axes[0]]
                            if not isinstance(ax, UnsliceableDatacubeAxis):
                                fval = ax.to_float(val)
                                # slice polytope along the value and add sliced polytope to list of polytopes in memory
                                sliced_poly = slice(poly, grid_axes[0], fval, slice_axis_idx)
                                sliced_polys.append(sliced_poly)
                        # decide if axis should be compressed or not according to polytope
                        # NOTE: actually the first grid axis will never be compressed
                        axis_compressed = (grid_axes[0] in self.compressed_axes)

                        # if it's not compressed, need to separate into different nodes to append to the tree
                        for i, found_val in enumerate(found_vals):
                            found_val = self.remap_values(ax, found_val)
                            child_polytopes = [p for p in polytopes if p != poly]
                            if sliced_polys[i]:
                                child_polytopes.append(sliced_polys[i])

                            second_axis_vals = mapper_transformation.second_axis_vals([found_val])
                            flattened_path = {grid_axes[0]: (found_val,)}
                            # get second axis children through slicing
                            children = _slice_second_grid_axis(
                                grid_axes[1], child_polytopes, datacube, datacube_transformations, second_axis_vals, flattened_path)
                            # If this node used to have children but now has none due to filtering, skip it.
                            if not children:
                                continue
                            if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                                found_val = [str(found_val)]

                            # TODO: remap the found_val using self.remap_values like in the hullslicer

                            # TODO: when we have an axis that we would like to merge with another, we should skip the node creation here
                            # and instead keep/cache the value to merge with the node from before??

                            qube_node = Qube.make(key=grid_axes[0],
                                                  values=QEnum([found_val]),
                                                  metadata={},
                                                  children=children)
                            result.append(qube_node)

            for i, child in enumerate(q.children):
                # find polytopes which are defined on axis child.key
                polytopes_on_axis = find_polytopes_on_axis(child.key, polytopes)

                # TODO: here add the axes to datacube backend with transformations for child.key

                # here now first change the values in the polytopes on the axis to reflect the axis type

                for poly in polytopes_on_axis:
                    ax = datacube._axes[child.key]
                    # find extents of polytope on child.key
                    lower, upper, slice_axis_idx = poly.extents(child.key)

                    # # find values on child that are within extents
                    # # here first change the child values of the datacube ie the Qubed tree to their right type with the transformation
                    # modified_vals = change_datacube_val_types(child, datacube_transformations)

                    # # here use the axis to transform lower and upper to right type too
                    # new_lower, new_upper = transform_upper_lower(child.key, lower, upper, datacube)
                    # found_vals = [v for v in modified_vals if new_lower <= v <= new_upper]
                    found_vals = self.find_values_between(poly, ax, child, datacube, lower, upper)

                    if len(found_vals) == 0:
                        continue

                    # slice polytope along each value on child and keep resulting polytopes in memory
                    sliced_polys = []
                    for val in found_vals:
                        # ax = datacube._axes[child.key]
                        if not isinstance(ax, UnsliceableDatacubeAxis):
                            fval = ax.to_float(val)
                            # slice polytope along the value and add sliced polytope to list of polytopes in memory
                            sliced_poly = slice(poly, child.key, fval, slice_axis_idx)
                            sliced_polys.append(sliced_poly)
                    # decide if axis should be compressed or not according to polytope
                    axis_compressed = (child.key in self.compressed_axes)
                    # if it's not compressed, need to separate into different nodes to append to the tree
                    if not axis_compressed and len(found_vals) > 1:
                        for i, found_val in enumerate(found_vals):
                            found_val = self.remap_values(ax, found_val)
                            child_polytopes = [p for p in polytopes if p != poly]
                            if sliced_polys[i]:
                                child_polytopes.append(sliced_polys[i])
                            children = _slice(child, child_polytopes, datacube, datacube_transformations)
                            # If this node used to have children but now has none due to filtering, skip it.
                            if child.children and not children:
                                continue
                            if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                                found_val = [str(found_val)]

                            # TODO: when we have an axis that we would like to merge with another, we should skip the node creation here
                            # and instead keep/cache the value to merge with the node from before??

                            qube_node = Qube.make(key=child.key,
                                                  values=QEnum(found_val),
                                                  metadata=child.metadata,
                                                  children=children)
                            result.append(qube_node)
                    else:
                        # if it's compressed, then can add all found values in a single node
                        child_polytopes = [p for p in polytopes if p != poly]
                        child_polytopes.extend(
                            [sliced_poly_ for sliced_poly_ in sliced_polys if sliced_poly_ is not None])
                        # create children
                        children = _slice(child, child_polytopes, datacube, datacube_transformations)
                        # If this node used to have children but now has none due to filtering, skip it.
                        if child.children and not children:
                            continue

                        new_found_vals = []
                        for found_val in found_vals:
                            found_val = self.remap_values(ax, found_val)
                            if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                                new_found_vals.append(str(found_val))
                            else:
                                new_found_vals.append(found_val)

                        result.extend([Qube.make(
                            key=child.key,
                            values=QEnum(new_found_vals),
                            metadata=child.metadata,
                            children=children
                        )])

            return result

        return Qube.root_node(_slice(q, polytopes_to_slice, datacube, datacube_transformations))

    def actual_slice(self, q: Qube, polytopes_to_slice, datacube, datacube_transformations):

        groups, input_axes = group(polytopes_to_slice)
        combinations = tensor_product(groups)

        sub_trees = []

        # NOTE: could optimise here if we know combinations will always be for one request.
        # Then we do not need to create a new index tree and merge it to request, but can just
        # directly work on request and return it...

        for c in combinations:
            new_c = []
            for combi in c:
                if isinstance(combi, list):
                    new_c.extend(combi)
                else:
                    new_c.append(combi)
            final_polys = []
            for poly in new_c:
                if isinstance(poly, Product):
                    final_polys.extend(poly.polytope())
                else:
                    final_polys.append(poly)

            # Get the sliced Qube for each combi
            r = self._actual_slice(q, final_polys, datacube, datacube_transformations)
            sub_trees.append(r)

        final_tree = sub_trees[0]

        for sub_tree in sub_trees[1:]:
            union(final_tree, sub_tree)
        return final_tree

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        self.find_compressed_axes(datacube, polytopes)
        self.pre_process_polytopes(datacube, polytopes)
        assert isinstance(datacube, QubedDatacube)
        tree = self.actual_slice(datacube.q, polytopes, datacube,
                                 datacube.datacube_transformations)
        return tree
