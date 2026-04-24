import math

import numpy as np

from polytope_feature.polytope_rs import (
    first_axis_vals_healpix_nested,
    healpix_longitudes,
    unmap,
)

from ..datacube_mappers import DatacubeMapper


class NestedHealpixGridMapper(DatacubeMapper):
    def __init__(
        self,
        base_axis,
        mapped_axes,
        resolution,
        md5_hash=None,
        local_area=[],
        axis_reversed=None,
        mapper_options=None,
    ):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self.is_irregular = False
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        self._first_axis_vals = self.first_axis_vals()
        self._first_axis_vals_np_rounded = -np.round(np.array(self._first_axis_vals), decimals=8)
        self.compressed_grid_axes = [self._mapped_axes[1]]
        self.Nside = self._resolution
        self.k = int(math.log2(self.Nside))
        self.Npix = 12 * self.Nside * self.Nside
        self.Ncap = (self.Nside * (self.Nside - 1)) << 1
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)
        if self._axis_reversed[mapped_axes[1]]:
            raise NotImplementedError("Healpix grid with second axis in decreasing order is not supported")
        if not self._axis_reversed[mapped_axes[0]]:
            raise NotImplementedError("Healpix grid with first axis in increasing order is not supported")

        if local_area != []:
            raise NotImplementedError("Local area grid not implemented for healpix grids")

    def first_axis_vals(self):
        return first_axis_vals_healpix_nested(self._resolution)

    def map_first_axis(self, lower, upper):
        axis_lines = self._first_axis_vals
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        tol = 1e-8
        first_val = [i for i in self._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
        idx = self._first_axis_vals.index(first_val)

        values = self.HEALPix_longitudes(idx)
        return values

    def second_axis_vals_from_idx(self, first_val_idx):
        values = self.HEALPix_longitudes(first_val_idx)
        return values

    def HEALPix_nj(self, i):
        assert self._resolution > 0
        ni = 4 * self._resolution - 1
        assert i < ni

        if i < self._resolution:
            return 4 * (i + 1)
        elif i < 3 * self._resolution:
            return 4 * self._resolution
        else:
            return self.HEALPix_nj(ni - 1 - i)

    def HEALPix_longitudes(self, i):
        return healpix_longitudes(i, self._resolution)

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def unmap(self, first_val, second_vals, unmapped_idx=None):
        return unmap(
            self._first_axis_vals,
            first_val[0],
            second_vals,
            self.Nside,
            self.Npix,
            self.Ncap,
            self.k,
            self._resolution,
        )


# md5 grid hash in form {resolution : hash}
_md5_hash = {
    1024: "cbda19e48d4d7e5e22641154878b9b22",
    512: "47efaa0853e70948a41d5225e7653194",
    128: "f3dfeb7a5bbbdd13a20d10fdb3797c71",
}
