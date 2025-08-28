import numpy as np
import pandas as pd
from qubed import Qube
from qubed.value_types import QEnum

from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.transformations.datacube_mappers.datacube_mappers import DatacubeMapper
from ..utility.combinatorics import (
    find_polytope_combinations,
    find_polytopes_on_axis,
    group,
    tensor_product,
)
from .engine import Engine
from .slicing_tools import slice
from copy import deepcopy


class QubedSlicer(Engine):
    # TODO: this slicer is very similar to the hullslicer, but just creating a different type of tree...
    # try to abstract the object we create and unify both slicer methods, which act on 1D space...
    def __init__(self):
        self.ax_is_unsliceable = {}
        self.compressed_axes = []
        self.remapped_vals = {}

    def find_datacube_vals():
        # TODO
        pass

    def find_values_between(self, polytope, ax, node, datacube, lower, upper, path=None):
        if isinstance(ax, UnsliceableDatacubeAxis):
            filtered = [(i, v) for i, v in enumerate(node.values) if lower <= v <= upper]
            indices, values = zip(*filtered) if filtered else ([], [])
            return values, indices

        tol = ax.tol
        lower = ax.from_float(lower - tol)
        upper = ax.from_float(upper + tol)
        method = polytope.method
        values, indexes = datacube.get_indices(path, node, ax, lower, upper, method)
        return values, indexes

    def get_sliced_polys(self, found_vals, ax, child_name, poly, slice_axis_idx):
        sliced_polys = []
        for val in found_vals:
            if not isinstance(ax, UnsliceableDatacubeAxis):
                fval = ax.to_float(val)
                # slice polytope along the value and add sliced polytope to list of polytopes in memory
                sliced_poly = slice(poly, child_name, fval, slice_axis_idx)
                sliced_polys.append(sliced_poly)
        return sliced_polys

    def find_children_polytopes(self, polytopes, poly, sliced_polys):
        child_polytopes = [p for p in polytopes if p != poly]
        child_polytopes.extend([sliced_poly_ for sliced_poly_ in sliced_polys if sliced_poly_ is not None])
        return child_polytopes

    def find_new_vals(self, found_vals, ax):
        new_found_vals = []
        for found_val in found_vals:
            found_val = self.remap_values(ax, found_val)
            # TODO: use unmap_path_key here with the transformations instead
            if isinstance(found_val, pd.Timedelta) or isinstance(found_val, pd.Timestamp):
                new_found_vals.append(str(found_val))
            else:
                new_found_vals.append(found_val)
        return new_found_vals

    def build_branch(
        self,
        real_uncompressed_axis,
        found_vals,
        sliced_polys,
        polytopes,
        poly,
        child,
        datacube,
        datacube_transformations,
        ax,
        idxs=None,
        metadata_idx_stack=None,
    ):
        final_children_and_vals = []
        if real_uncompressed_axis:
            for i, found_val in enumerate(found_vals):
                if i < len(sliced_polys):
                    sliced_polys_ = [sliced_polys[i]]
                else:
                    sliced_polys_ = sliced_polys
                child_polytopes = self.find_children_polytopes(polytopes, poly, sliced_polys_)
                if idxs:
                    current_metadata_idx_stack = metadata_idx_stack + [[idxs[i]]]
                children = self._slice(child, child_polytopes, datacube, datacube_transformations,
                                       current_metadata_idx_stack)
                # If this node used to have children but now has none due to filtering, skip it.
                if child.children and not children:
                    continue

                new_found_vals = self.find_new_vals([found_val], ax)

                if idxs:
                    request_child_val = (children, new_found_vals, current_metadata_idx_stack)
                else:
                    request_child_val = (children, new_found_vals)
                final_children_and_vals.append(request_child_val)
        else:
            # if it's compressed, then can add all found values in a single node
            child_polytopes = self.find_children_polytopes(polytopes, poly, sliced_polys)
            # create children
            if idxs:
                current_metadata_idx_stack = metadata_idx_stack + [idxs]
            children = self._slice(child, child_polytopes, datacube, datacube_transformations,
                                   current_metadata_idx_stack)
            # If this node used to have children but now has none due to filtering, skip it.
            if child.children and not children:
                return None

            new_found_vals = self.find_new_vals(found_vals, ax)
            if idxs:
                request_child_val = (children, new_found_vals, current_metadata_idx_stack)
            else:
                request_child_val = (children, new_found_vals)
            final_children_and_vals.append(request_child_val)

        if len(final_children_and_vals) == 0:
            return None
        return final_children_and_vals

    def _slice(self, q: Qube, polytopes, datacube, datacube_transformations, metadata_idx_stack=None) -> list[Qube]:
        result = []

        if metadata_idx_stack is None:
            metadata_idx_stack = [[0]]

        for i, child in enumerate(q.children):
            # find polytopes which are defined on axis child.key
            polytopes_on_axis = find_polytopes_on_axis(child.key, polytopes)

            # TODO: here add the axes to datacube backend with transformations for child.key
            # TODO: update the datacube axis_options before we dynamically change the axes

            # TODO: this is slow... will need to make it faster and only do this when we need...
            datacube.add_axes_dynamically(child)

            # here now first change the values in the polytopes on the axis to reflect the axis type
            for poly in polytopes_on_axis:
                ax = datacube._axes[child.key]
                # find extents of polytope on child.key
                lower, upper, slice_axis_idx = poly.extents(child.key)

                # find values on child that are within extents
                found_vals, idxs = self.find_values_between(poly, ax, child, datacube, lower, upper)

                # TODO: find the indexes of the found_vals wrt child.values, to extract the right metadata that we want to keep inside self.build_branch

                if len(found_vals) == 0:
                    continue

                sliced_polys = self.get_sliced_polys(found_vals, ax, child.key, poly, slice_axis_idx)
                # decide if axis should be compressed or not according to polytope
                axis_compressed = child.key in self.compressed_axes
                real_uncompressed_axis = not axis_compressed and len(found_vals) > 1
                final_children_and_vals = self.build_branch(
                    real_uncompressed_axis,
                    found_vals,
                    sliced_polys,
                    polytopes,
                    poly,
                    child,
                    datacube,
                    datacube_transformations,
                    ax,
                    idxs,
                    metadata_idx_stack
                )

                if final_children_and_vals is None:
                    continue

                def find_metadata(metadata_idx):
                    metadata = {}
                    for k, vs in child.metadata.items():
                        metadata_depth = len(vs.shape)
                        relevant_metadata_idxs = metadata_idx[:metadata_depth]
                        ix = np.ix_(*relevant_metadata_idxs)
                        metadata[k] = vs[ix]
                    return metadata

                for children, new_found_vals, current_metadata_idxs in final_children_and_vals:
                    metadata = find_metadata(current_metadata_idxs)
                    qube_node = Qube.make_node(
                        key=child.key, values=QEnum(new_found_vals), metadata=metadata, children=children
                    )
                    if not children:
                        # We've reached the end of the qube
                        # qube_node.sliced_polys = sliced_polys
                        qube_node.sliced_polys = polytopes
                    result.append(qube_node)

        return result

    def slice_grid_axes(self, q: Qube, datacube, datacube_transformations):
        # TODO: here, instead of checking if the qube is at the leaves, we instead give it the sub-tree and go to its leaves
        # TODO: we then find the remaining sliced_polys to continue slicing and slice along lat + lon like before
        # TODO: we then return the completed tree
        compressed_leaves = [leaf for leaf in q.compressed_leaf_nodes()]
        actual_leaves = deepcopy(compressed_leaves)
        for j, leaf in enumerate(actual_leaves):
            # for leaf in q.compressed_leaf_nodes():
            result = []
            mapper_transformation = None
            for transformation in datacube_transformations:
                if isinstance(transformation, DatacubeMapper):
                    mapper_transformation = transformation
            if not mapper_transformation:
                # There is no grid mapping
                pass
            else:
                grid_axes = mapper_transformation._mapped_axes()
                polytopes = leaf.sliced_polys

                # Handle first grid axis
                polytopes_on_axis = find_polytopes_on_axis(grid_axes[0], polytopes)

                for poly in polytopes_on_axis:
                    ax = datacube._axes[grid_axes[0]]
                    lower, upper, slice_axis_idx = poly.extents(grid_axes[0])

                    found_vals, _ = self.find_values_between(poly, ax, None, datacube, lower, upper)

                    if len(found_vals) == 0:
                        continue

                    sliced_polys = self.get_sliced_polys(found_vals, ax, grid_axes[0], poly, slice_axis_idx)
                    # decide if axis should be compressed or not according to polytope
                    # NOTE: actually the first grid axis will never be compressed

                    # if it's not compressed, need to separate into different nodes to append to the tree
                    for i, found_val in enumerate(found_vals):
                        found_val = self.remap_values(ax, found_val)
                        child_polytopes = [p for p in polytopes if p != poly]
                        if sliced_polys[i]:
                            child_polytopes.append(sliced_polys[i])

                        second_axis_vals = mapper_transformation.second_axis_vals([found_val])
                        flattened_path = {grid_axes[0]: (found_val,)}
                        # get second axis children through slicing
                        children = self._slice_second_grid_axis(
                            grid_axes[1],
                            child_polytopes,
                            datacube,
                            datacube_transformations,
                            second_axis_vals,
                            flattened_path,
                        )
                        # If this node used to have children but now has none due to filtering, skip it.
                        if not children:
                            continue

                        qube_node = Qube.make_node(
                            key=grid_axes[0], values=QEnum([found_val]), metadata={}, children=children
                        )
                        result.append(qube_node)
            # leaf.children = result
            compressed_leaves[j].children = result

    def _slice_second_grid_axis(
        self, axis_name, polytopes, datacube, datacube_transformations, second_axis_vals, path
    ) -> list[Qube]:
        result = []
        polytopes_on_axis = find_polytopes_on_axis(axis_name, polytopes)

        for poly in polytopes_on_axis:
            ax = datacube._axes[axis_name]
            lower, upper, slice_axis_idx = poly.extents(axis_name)

            found_vals, _ = self.find_values_between(poly, ax, None, datacube, lower, upper, path)

            if len(found_vals) == 0:
                continue

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

            result.extend([Qube.make_node(key=axis_name, values=QEnum(
                new_found_vals), metadata={"result": []}, children={})])
        return result

    def slice_tree(self, datacube, final_polys):
        q = datacube.q
        datacube_transformations = datacube.datacube_transformations
        # create sub-qube without grid first
        request_qube = Qube.make_root(self._slice(q, final_polys, datacube, datacube_transformations))
        # recompress this sub-qube
        request_qube = request_qube.compress_w_leaf_attrs("sliced_polys")
        # complete the qube with grid axes and return it
        self.slice_grid_axes(request_qube, datacube, datacube_transformations)
        return request_qube

    def build_tree(self, polytopes_to_slice, datacube):
        groups, input_axes = group(polytopes_to_slice)
        combinations = tensor_product(groups)

        sub_trees = []

        for c in combinations:
            final_polys = find_polytope_combinations(c)

            # Get the sliced Qube for each combi
            r = self.slice_tree(datacube, final_polys)
            sub_trees.append(r)

        final_tree = sub_trees[0]

        for sub_tree in sub_trees[1:]:
            final_tree | sub_tree
        return final_tree
