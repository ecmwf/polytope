import bisect
import math

from ..datacube_mappers import DatacubeMapper


class NestedHealpixGridMapper(DatacubeMapper):
    def __init__(self, base_axis, mapped_axes, resolution, md5_hash=None, local_area=[], axis_reversed=None):
        # TODO: if local area is not empty list, raise NotImplemented
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = {mapped_axes[0]: True, mapped_axes[1]: False}
        self._first_axis_vals = self.first_axis_vals()
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
        start = (
            step / 2.0 if i < self._resolution or 3 * self._resolution - 1 < i or (i + self._resolution) % 2 else 0.0
        )

        longitudes = [start + n * step for n in range(Nj)]

        return longitudes

    def map_second_axis(self, first_val, lower, upper):
        axis_lines = self.second_axis_vals(first_val)
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def axes_idx_to_healpix_idx(self, first_idx, second_idx):
        idx = 0
        for i in range(self._resolution - 1):
            if i != first_idx:
                idx += 4 * (i + 1)
            else:
                idx += second_idx
                return idx
        for i in range(self._resolution - 1, 3 * self._resolution):
            if i != first_idx:
                idx += 4 * self._resolution
            else:
                idx += second_idx
                return idx
        for i in range(3 * self._resolution, 4 * self._resolution - 1):
            if i != first_idx:
                idx += 4 * (4 * self._resolution - 1 - i + 1)
            else:
                idx += second_idx
                return idx

    def find_second_idx(self, first_val, second_val):
        tol = 1e-10
        second_axis_vals = self.second_axis_vals(first_val)
        second_idx = bisect.bisect_left(second_axis_vals, second_val - tol)
        return second_idx

    def unmap_first_val_to_start_line_idx(self, first_val):
        tol = 1e-8
        first_val = [i for i in self._first_axis_vals if first_val - tol <= i <= first_val + tol][0]
        first_idx = self._first_axis_vals.index(first_val)
        idx = 0
        for i in range(self._resolution - 1):
            if i != first_idx:
                idx += 4 * (i + 1)
            else:
                return idx
        for i in range(self._resolution - 1, 3 * self._resolution):
            if i != first_idx:
                idx += 4 * self._resolution
            else:
                return idx
        for i in range(3 * self._resolution, 4 * self._resolution - 1):
            if i != first_idx:
                idx += 4 * (4 * self._resolution - 1 - i + 1)
            else:
                return idx

    def unmap(self, first_val, second_val):
        tol = 1e-8
        first_value = [i for i in self._first_axis_vals if first_val[0] - tol <= i <= first_val[0] + tol][0]
        first_idx = self._first_axis_vals.index(first_value)
        second_val = [i for i in self.second_axis_vals(first_val) if second_val[0] - tol <= i <= second_val[0] + tol][0]
        second_idx = self.second_axis_vals(first_val).index(second_val)
        healpix_index = self.axes_idx_to_healpix_idx(first_idx, second_idx)
        # TODO: here do conversion of ring to nested healpix representation before returning
        healpix_index = self.ring_to_nested(healpix_index)
        return healpix_index

    def div_03(self, a, b):
        t = 1 if a >= (b << 1) else 0
        a -= t * (b << 1)
        return (t << 1) + (1 if a >= b else 0)

    def pll(self, f):
        pll_values = [1, 3, 5, 7, 0, 2, 4, 6, 1, 3, 5, 7]
        return pll_values[f]

    def to_nest(self, f, ring, Nring, phi, shift):
        r = int(((2 + (f >> 2)) << self.k) - ring - 1)
        p = int(2 * phi - self.pll(f) * Nring - shift - 1)
        if p >= 2 * self.Nside:
            p -= 8 * self.Nside
        i = int((r + p)) >> 1
        j = int((r - p)) >> 1

        return self.fij_to_nest(f, i, j, self.k)

    def fij_to_nest(self, f, i, j, k):
        return (f << (2 * k)) + self.nest_encode_bits(i) + (self.nest_encode_bits(j) << 1)

    def nest_encode_bits(self, i):
        __masks = [
            0x00000000FFFFFFFF,
            0x0000FFFF0000FFFF,
            0x00FF00FF00FF00FF,
            0x0F0F0F0F0F0F0F0F,
            0x3333333333333333,
            0x5555555555555555,
        ]
        i = int(i)
        b = i & __masks[0]
        b = (b ^ (b << 16)) & __masks[1]
        b = (b ^ (b << 8)) & __masks[2]
        b = (b ^ (b << 4)) & __masks[3]
        b = (b ^ (b << 2)) & __masks[4]
        b = (b ^ (b << 1)) & __masks[5]
        return b

    def ring_to_nested(self, idx):
        if idx < self.Ncap:
            # North polar cap
            Nring = (1 + self.int_sqrt(2 * idx + 1)) >> 1
            phi = 1 + idx - 2 * Nring * (Nring - 1)
            f = self.div_03(phi - 1, Nring)
            return self.to_nest(f, Nring, Nring, phi, 0)

        if self.Npix - self.Ncap <= idx:
            # South polar cap
            Nring = (1 + self.int_sqrt(2 * self.Npix - 2 * idx - 1)) >> 1
            phi = 1 + idx + 2 * Nring * (Nring - 1) + 4 * Nring - self.Npix
            ring = 4 * self.Nside - Nring  # (from South pole)
            f = self.div_03(phi - 1, Nring) + 8
            return self.to_nest(f, ring, Nring, phi, 0)
        else:
            # Equatorial belt
            ip = idx - self.Ncap
            tmp = ip >> (self.k + 2)

            phi = ip - tmp * 4 * self.Nside + 1
            ring = tmp + self.Nside

            ifm = 1 + ((phi - 1 - ((1 + tmp) >> 1)) >> self.k)
            ifp = 1 + ((phi - 1 - ((1 - tmp + 2 * self.Nside) >> 1)) >> self.k)
            f = (ifp | 4) if ifp == ifm else (ifp if ifp < ifm else (ifm + 8))

            return self.to_nest(f, ring, self.Nside, phi, ring & 1)

    def int_sqrt(self, i):
        return int(math.sqrt(i + 0.5))


# md5 grid hash in form {resolution : hash}
_md5_hash = {}
