import math
from copy import copy
from typing import List

from ..datacube.backends.datacube import Datacube
# from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope, Product
from ..utility.combinatorics import group, tensor_product
from ..utility.exceptions import UnsliceableShapeError
# from ..utility.list_tools import unique
from ..utility.slicing_tools import slice
from .engine import Engine


class HullSlicer(Engine):
    def __init__(self):
        self.ax_is_unsliceable = {}
        self.axis_values_between = {}
        self.has_value = {}
        self.sliced_polytopes = {}
        self.remapped_vals = {}
        self.compressed_axes = []

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

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]):
        # Determine list of axes to compress
        combinations = self.prep_extraction(datacube, polytopes)

        request = TensorIndexTree()

        # NOTE: could optimise here if we know combinations will always be for one request.
        # Then we do not need to create a new index tree and merge it to request, but can just
        # directly work on request and return it...

        for c in combinations:
            r = self.extract_combi_tree(c, datacube)
            request.merge(r)
        return request

    def extract_combi_tree(self, c, datacube):
        r = TensorIndexTree()
        final_polys = self.find_final_combi(c)
        r["unsliced_polytopes"] = set(final_polys)
        current_nodes = [r]
        for ax in datacube.axes.values():
            next_nodes = []
            interm_next_nodes = []
            for node in current_nodes:
                self._build_branch(ax, node, datacube, interm_next_nodes)
                next_nodes.extend(interm_next_nodes)
                interm_next_nodes = []
            current_nodes = next_nodes
        return r
