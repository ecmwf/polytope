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

    def _build_child(self, polytope, ax, node, datacube, values, next_nodes, slice_axis_idx, i, num_branches):
        if self.ax_is_unsliceable[ax.name]:
            self._build_unsliceable_child(
                polytope, ax, node, datacube, values, next_nodes, slice_axis_idx
            )
        else:
            if len(values) == 0 and len(node.children) == 0 and i == num_branches - 1:
                node.remove_branch()
            self._build_sliceable_child(
                polytope, ax, node, datacube, values, next_nodes, slice_axis_idx
            )

    def get_polytope_values_on_ax(self, ax, node, datacube):
        right_unsliced_polytopes = []
        all_values = []
        slice_axis_idx = None

        for polytope in node["unsliced_polytopes"]:
            if ax.name in polytope._axes:

                if ax.name not in self.compressed_axes:
                    right_unsliced_polytopes.append(polytope)
                    lower, upper, slice_axis_idx = polytope.extents(ax.name)
                    if self.ax_is_unsliceable[ax.name]:
                        values = [lower]
                        all_values.append(values)
                    else:
                        values = self.find_values_between(polytope, ax, node, datacube, lower, upper)
                        all_values.append(values)
                else:
                    if not right_unsliced_polytopes:
                        right_unsliced_polytopes.append(polytope)
                    lower, upper, _slice_axis_idx = polytope.extents(ax.name)
                    if not slice_axis_idx:
                        slice_axis_idx = _slice_axis_idx
                    if not all_values:
                        # Make sure that we have an inner list
                        all_values.append([])
                    if self.ax_is_unsliceable[ax.name]:
                        all_values[0].append(lower)
                    else:
                        values = self.find_values_between(polytope, ax, node, datacube, lower, upper)
                        all_values[0].extend(values)
        return (all_values, right_unsliced_polytopes, slice_axis_idx)

    def _build_branch(self, ax, node, datacube, next_nodes):
        (all_values, right_unsliced_polytopes, slice_axis_idx) = self.get_polytope_values_on_ax(ax, node, datacube)
        num_branches = len(right_unsliced_polytopes)
        for i, unsliced_polytope in enumerate(right_unsliced_polytopes):
            values = all_values[i]
            self._build_child(unsliced_polytope, ax, node, datacube, values,
                              next_nodes, slice_axis_idx, i, num_branches)
        del node["unsliced_polytopes"]

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

    def alternative_extract_combi_tree(self, c, datacube):
        # Recursively loop through the datacube.axes_tree and built result tree "backwards" ie from leaves onwards

        def _build_branch(polytopes, datacube):
            pass

        final_polys = self.find_final_combi(c)

        # TODO: create a root_node object in the TensorIndexTree
        return
