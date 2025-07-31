import math
from typing import List

from ..datacube.backends.datacube import Datacube
from ..datacube.datacube_axis import UnsliceableDatacubeAxis
from ..shapes import ConvexPolytope, Product
from ..utility.list_tools import unique


class Engine:
    def __init__(self):
        pass

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

    def pre_process_polytopes(self, datacube, polytopes):
        for p in polytopes:
            if isinstance(p, Product):
                for poly in p.polytope():
                    self._unique_continuous_points(poly, datacube)
            else:
                self._unique_continuous_points(p, datacube)

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
        self.find_compressed_axes(datacube, polytopes)
        self.remove_compressed_axis_in_union(polytopes)
        self.pre_process_polytopes(datacube, polytopes)
        tree = self.build_tree(polytopes, datacube)
        return tree
