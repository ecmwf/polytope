import math

import numpy as np

from ..datacube_mappers import DatacubeMapper


class NestedHealpixGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, md5_hash=None, local_area=[], axis_reversed=None):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
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

    def first_axis_vals(self):
        rad2deg = 180 / math.pi
        vals = [0] * (4 * self._resolution - 1)

        # Polar caps
        for i in range(1, self._resolution):
            val = 90 - (rad2deg * math.acos(1 - (i * i / (3 * self._resolution * self._resolution))))
            vals[i - 1] = val
            vals[4 * self._resolution - 1 - i] = -val
        # Equatorial belts
        for i in range(self._resolution, 2 * self._resolution):
            val = 90 - (rad2deg * math.acos((4 * self._resolution - 2 * i) / (3 * self._resolution)))
            vals[i - 1] = val
            vals[4 * self._resolution - 1 - i] = -val
        # Equator
        vals[2 * self._resolution - 1] = 0
        return vals

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
        Nj = self.HEALPix_nj(i)
        step = 360.0 / Nj
        start = np.where(
            (i < self._resolution) | (3 * self._resolution - 1 < i) | ((i + self._resolution) % 2 == 1), step / 2.0, 0.0
        )
        longitudes = start + np.arange(Nj) * step
        return longitudes

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_healpix_idx(self, first_idx, second_idx):
        res = self._resolution
        sum1 = 2 * (res - 1) * res
        sum2 = 2 * (((res - 1) * res) - ((4 * res - 1 - first_idx) * (4 * res - first_idx)))

        if first_idx < res - 1:
            return (2 * first_idx * (first_idx + 1)) + second_idx
        elif first_idx < 3 * res:
            return sum1 + (first_idx - (res - 1)) * (4 * res) + second_idx
        else:
            return sum1 + (2 * res + 1) * (4 * res) + sum2 + second_idx

    def unmap(self, first_val, second_vals):
        # Convert to NumPy array for fast computation
        idx = np.searchsorted(self._first_axis_vals_np_rounded, -np.round(first_val[0], decimals=8))
        if idx >= len(self._first_axis_vals_np_rounded):
            return None
        second_axis_vals = np.round(np.array(self.second_axis_vals_from_idx(idx)), decimals=8)
        second_vals = np.round(np.array(second_vals), decimals=8)
        second_idxs = np.searchsorted(second_axis_vals, second_vals)
        valid_mask = second_idxs < len(second_axis_vals)
        if not np.all(valid_mask):
            return None
        healpix_idxs = [self.axes_idx_to_healpix_idx(idx, sec_idx) for sec_idx in second_idxs]
        return self.ring_to_nested(np.asarray(healpix_idxs))

    def div_03(self, a, b):
        """Vectorized version of div_03"""
        t = np.where(a >= (b << 1), 1, 0)
        a -= t * (b << 1)
        return (t << 1) + np.where(a >= b, 1, 0)

    def pll(self, f):
        """Vectorized lookup for PLL values"""
        pll_values = np.array([1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7])
        return pll_values[f]

    def to_nest(self, f, ring, Nring, phi, shift):
        """Vectorized to_nest conversion"""
        r = ((2 + (f >> 2)) << self.k) - ring - 1
        p = 2 * phi - self.pll(f) * Nring - shift - 1
        p = np.where(p >= 2 * self.Nside, p - 8 * self.Nside, p)

        i = (r + p) >> 1
        j = (r - p) >> 1
        return self.fij_to_nest(f, i, j, self.k)

    def fij_to_nest(self, f, i, j, k):
        """Vectorized nest encoding"""
        return (
            # (f.astype(np.uint64) << np.uint64(2 * k))
            (f.astype(object) << (2 * k))
            + self.nest_encode_bits(i)
            + (self.nest_encode_bits(j).astype(np.uint64) << np.uint64(1))
        )

    def nest_encode_bits(self, i):
        """Vectorized bit manipulation for HEALPix indexing"""
        __masks = np.array(
            [
                0x00000000FFFFFFFF,
                0x0000FFFF0000FFFF,
                0x00FF00FF00FF00FF,
                0x0F0F0F0F0F0F0F0F,
                0x3333333333333333,
                0x5555555555555555,
            ],
            dtype=np.uint64,
        )

        b = i.astype(np.uint64) & __masks[0]
        b = (b ^ (b << np.uint64(16))) & __masks[1]
        b = (b ^ (b << np.uint64(8))) & __masks[2]
        b = (b ^ (b << np.uint64(4))) & __masks[3]
        b = (b ^ (b << np.uint64(2))) & __masks[4]
        b = (b ^ (b << np.uint64(1))) & __masks[5]
        return b

    def int_sqrt(self, x):
        """Efficient integer square root for arrays"""
        return np.sqrt(x + 0.5).astype(int)

    def ring_to_nested(self, idx):
        """Vectorized ring_to_nested conversion"""
        # idx = np.asarray(idx)  # Ensure input is an array

        north_mask = idx < self.Ncap
        south_mask = self.Npix - self.Ncap <= idx

        # North polar cap
        Nring_north = (1 + self.int_sqrt(2 * idx + 1)) >> 1
        phi_north = 1 + idx - 2 * Nring_north * (Nring_north - 1)
        f_north = self.div_03(phi_north - 1, Nring_north)
        nested_north = self.to_nest(f_north, Nring_north, Nring_north, phi_north, 0)

        # South polar cap
        Nring_south = (1 + self.int_sqrt(2 * self.Npix - 2 * idx - 1)) >> 1
        phi_south = 1 + idx + 2 * Nring_south * (Nring_south - 1) + 4 * Nring_south - self.Npix
        ring_south = 4 * self.Nside - Nring_south
        f_south = self.div_03(phi_south - 1, Nring_south) + 8
        nested_south = self.to_nest(f_south, ring_south, Nring_south, phi_south, 0)

        # Equatorial belt
        ip = idx - self.Ncap
        tmp = ip >> (self.k + 2)

        phi_equatorial = ip - tmp * 4 * self.Nside + 1
        ring_equatorial = tmp + self.Nside

        ifm = 1 + ((phi_equatorial - 1 - ((1 + tmp) >> 1)) >> self.k)
        ifp = 1 + ((phi_equatorial - 1 - ((1 - tmp + 2 * self.Nside) >> 1)) >> self.k)
        f_equatorial = np.where(ifp == ifm, ifp | 4, np.where(ifp < ifm, ifp, ifm + 8))

        nested_equatorial = self.to_nest(f_equatorial, ring_equatorial, self.Nside, phi_equatorial, ring_equatorial & 1)
        nested_result = np.empty_like(idx)  # Preallocate array for performance
        nested_result[north_mask] = nested_north[north_mask]
        nested_result[south_mask] = nested_south[south_mask]
        nested_result[~(north_mask | south_mask)] = nested_equatorial[~(north_mask | south_mask)]
        return nested_result


# md5 grid hash in form {resolution : hash}
_md5_hash = {
    1024: "cbda19e48d4d7e5e22641154878b9b22",
    512: "47efaa0853e70948a41d5225e7653194",
    128: "f3dfeb7a5bbbdd13a20d10fdb3797c71",
}
