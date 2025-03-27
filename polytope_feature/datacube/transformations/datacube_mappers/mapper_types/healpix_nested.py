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
        # self._cached_longitudes = {}
        self.k = int(math.log2(self.Nside))
        self.Npix = 12 * self.Nside * self.Nside
        self.Ncap = (self.Nside * (self.Nside - 1)) << 1
        # self._healpix_longitudes = {}
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)
        if self._axis_reversed[mapped_axes[1]]:
            raise NotImplementedError("Healpix grid with second axis in decreasing order is not supported")
        if not self._axis_reversed[mapped_axes[0]]:
            raise NotImplementedError("Healpix grid with first axis in increasing order is not supported")

    # def first_axis_vals(self):
    #     rad2deg = 180 / math.pi
    #     vals = [0] * (4 * self._resolution - 1)

    #     # Polar caps
    #     for i in range(1, self._resolution):
    #         val = 90 - (rad2deg * math.acos(1 - (i * i / (3 * self._resolution * self._resolution))))
    #         vals[i - 1] = val
    #         vals[4 * self._resolution - 1 - i] = -val
    #     # Equatorial belts
    #     for i in range(self._resolution, 2 * self._resolution):
    #         val = 90 - (rad2deg * math.acos((4 * self._resolution - 2 * i) / (3 * self._resolution)))
    #         vals[i - 1] = val
    #         vals[4 * self._resolution - 1 - i] = -val
    #     # Equator
    #     vals[2 * self._resolution - 1] = 0
    #     return vals

    def first_axis_vals(self):
        rad2deg = 180 / np.pi
        res = self._resolution
        total_size = 4 * res - 1
        vals = np.zeros(total_size)

        factor1 = 3 * res * res
        factor2 = 3 * res

        # Polar caps
        i_vals = np.arange(1, res)
        acos_vals = np.arccos(1 - (i_vals**2 / factor1)) * rad2deg
        vals[i_vals - 1] = 90 - acos_vals
        vals[total_size - i_vals] = -(90 - acos_vals)

        # Equatorial belts
        i_vals = np.arange(res, 2 * res)
        acos_vals = np.arccos((4 * res - 2 * i_vals) / factor2) * rad2deg
        vals[i_vals - 1] = 90 - acos_vals
        vals[total_size - i_vals] = -(90 - acos_vals)

        # Equator
        vals[2 * res - 1] = 0

        return vals.tolist()  # Convert back to list if needed

    def second_axis_vals(self, first_val):
        idx = np.searchsorted(self._first_axis_vals_np_rounded, -np.round(first_val[0], decimals=8))
        return self.second_axis_vals_from_idx(idx)

    def second_axis_vals_from_idx(self, first_val_idx):
        # if first_val_idx not in self._healpix_longitudes:
        #     self._healpix_longitudes[first_val_idx] = self.HEALPix_longitudes(first_val_idx)
        values = self.HEALPix_longitudes(first_val_idx)
        return values

    def HEALPix_nj(self, i):
        ni = 4 * self._resolution - 1
        if i < self._resolution:
            return 4 * (i + 1)
        elif i < 3 * self._resolution:
            return 4 * self._resolution
        else:
            return self.HEALPix_nj(ni - 1 - i)

    def HEALPix_longitudes(self, i):
        # if i in self._cached_longitudes:
        #     return self._cached_longitudes[i]
        # else:
        if True:
            Nj = self.HEALPix_nj(i)
            step = 360.0 / Nj
            start = (
                step / 2.0
                if i < self._resolution or 3 * self._resolution - 1 < i or (i + self._resolution) % 2
                else 0.0
            )
            longitudes = [start + n * step for n in range(Nj)]
            # self._cached_longitudes[i] = longitudes
        return longitudes

    def axes_idx_to_healpix_idx(self, first_idx, second_idx):
        res = self._resolution
        # Directly compute index without unnecessary loops
        if first_idx < res - 1:
            return sum(4 * (i + 1) for i in range(first_idx)) + second_idx
        elif first_idx < 3 * res:
            return sum(4 * (i + 1) for i in range(res - 1)) + (first_idx - (res - 1)) * (4 * res) + second_idx
        else:
            return (
                sum(4 * (i + 1) for i in range(res - 1))
                + (2 * res + 1) * (4 * res)
                + sum(4 * (4 * res - 1 - i) for i in range(3 * res, first_idx))
                + second_idx
            )

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
        return [self.ring_to_nested(self.axes_idx_to_healpix_idx(idx, sec_idx)) for sec_idx in second_idxs]

    # def div_03(self, a, b):
    #     t = 1 if a >= (b << 1) else 0
    #     a -= t * (b << 1)
    #     return (t << 1) + (1 if a >= b else 0)

    # def pll(self, f):
    #     pll_values = [1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7]
    #     return pll_values[f]

    # def to_nest(self, f, ring, Nring, phi, shift):
    #     r = int(((2 + (f >> 2)) << self.k) - ring - 1)
    #     p = int(2 * phi - self.pll(f) * Nring - shift - 1)
    #     if p >= 2 * self.Nside:
    #         p -= 8 * self.Nside
    #     i = int((r + p)) >> 1
    #     j = int((r - p)) >> 1

    #     return self.fij_to_nest(f, i, j, self.k)

    # def fij_to_nest(self, f, i, j, k):
    #     return (f << (2 * k)) + self.nest_encode_bits(i) + (self.nest_encode_bits(j) << 1)

    # def nest_encode_bits(self, i):
    #     __masks = [
    #         0x00000000FFFFFFFF,
    #         0x0000FFFF0000FFFF,
    #         0x00FF00FF00FF00FF,
    #         0x0F0F0F0F0F0F0F0F,
    #         0x3333333333333333,
    #         0x5555555555555555,
    #     ]
    #     i = int(i)
    #     b = i & __masks[0]
    #     b = (b ^ (b << 16)) & __masks[1]
    #     b = (b ^ (b << 8)) & __masks[2]
    #     b = (b ^ (b << 4)) & __masks[3]
    #     b = (b ^ (b << 2)) & __masks[4]
    #     b = (b ^ (b << 1)) & __masks[5]
    #     return b

    # def ring_to_nested(self, idx):
    #     if idx < self.Ncap:
    #         # North polar cap
    #         Nring = (1 + self.int_sqrt(2 * idx + 1)) >> 1
    #         phi = 1 + idx - 2 * Nring * (Nring - 1)
    #         f = self.div_03(phi - 1, Nring)
    #         return self.to_nest(f, Nring, Nring, phi, 0)

    #     if self.Npix - self.Ncap <= idx:
    #         # South polar cap
    #         Nring = (1 + self.int_sqrt(2 * self.Npix - 2 * idx - 1)) >> 1
    #         phi = 1 + idx + 2 * Nring * (Nring - 1) + 4 * Nring - self.Npix
    #         ring = 4 * self.Nside - Nring  # (from South pole)
    #         f = self.div_03(phi - 1, Nring) + 8
    #         return self.to_nest(f, ring, Nring, phi, 0)
    #     else:
    #         # Equatorial belt
    #         ip = idx - self.Ncap
    #         tmp = ip >> (self.k + 2)

    #         phi = ip - tmp * 4 * self.Nside + 1
    #         ring = tmp + self.Nside

    #         ifm = 1 + ((phi - 1 - ((1 + tmp) >> 1)) >> self.k)
    #         ifp = 1 + ((phi - 1 - ((1 - tmp + 2 * self.Nside) >> 1)) >> self.k)
    #         f = (ifp | 4) if ifp == ifm else (ifp if ifp < ifm else (ifm + 8))

    #         return self.to_nest(f, ring, self.Nside, phi, ring & 1)

    # def int_sqrt(self, i):
    #     return int(math.sqrt(i + 0.5))

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
            (f.astype(np.uint64) << np.uint64(2 * k))
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
        idx = np.asarray(idx)  # Ensure input is an array

        # Create masks for different regions
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

        # Combine results using masks
        nested_result = np.where(north_mask, nested_north, np.where(south_mask, nested_south, nested_equatorial))
        return nested_result


# md5 grid hash in form {resolution : hash}
_md5_hash = {
    1024: "cbda19e48d4d7e5e22641154878b9b22",
    512: "47efaa0853e70948a41d5225e7653194",
    128: "f3dfeb7a5bbbdd13a20d10fdb3797c71",
}
