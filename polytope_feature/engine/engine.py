from typing import List
import math

from ..datacube.backends.datacube import Datacube
from ..datacube.tensor_index_tree import TensorIndexTree
from ..shapes import ConvexPolytope

from ..datacube.datacube_axis import UnsliceableDatacubeAxis

from ..utility.list_tools import unique

from ..shapes import ConvexPolytope, Product
from ..utility.combinatorics import group, tensor_product


class Engine:
    def __init__(self):
        pass

    # def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> TensorIndexTree:
    #     pass

    @staticmethod
    def default():
        from .hullslicer import HullSlicer

        return HullSlicer()

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

    def find_values_between(self, polytope, ax, node, datacube, lower, upper):
        tol = ax.tol
        lower = ax.from_float(lower - tol)
        upper = ax.from_float(upper + tol)
        flattened = node.flatten()
        method = polytope.method

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

    def prep_extraction(self, datacube, polytopes):
        # Determine list of axes to compress
        self.find_compressed_axes(datacube, polytopes)

        # remove compressed axes which are in a union
        self.remove_compressed_axis_in_union(polytopes)

        # Convert the polytope points to float type to support triangulation and interpolation
        for p in polytopes:
            if isinstance(p, Product):
                for poly in p.polytope():
                    self._unique_continuous_points(poly, datacube)
            else:
                self._unique_continuous_points(p, datacube)

        groups, input_axes = group(polytopes)
        datacube.validate(input_axes)
        combinations = tensor_product(groups)

        return combinations

    def find_final_combi(self, c):
        new_c = []
        for combi in c:
            if isinstance(combi, list):
                new_c.extend(combi)
            else:
                new_c.append(combi)
        # NOTE TODO: here some of the polys in new_c can be a Product shape instead of a ConvexPolytope
        # -> need to go through the polytopes in new_c and replace the Products with their sub-ConvexPolytopes
        final_polys = []
        for poly in new_c:
            if isinstance(poly, Product):
                final_polys.extend(poly.polytope())
            else:
                final_polys.append(poly)
        return final_polys

    def extract(self, datacube: Datacube, polytopes: List[ConvexPolytope]) -> TensorIndexTree:
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
