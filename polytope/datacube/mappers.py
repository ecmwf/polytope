import math
from abc import ABC, abstractmethod, abstractproperty


class GridMappers(ABC):
    @abstractproperty
    def _mapped_axes(self):
        pass

    @abstractproperty
    def _base_axis(self):
        pass

    @abstractproperty
    def _resolution(self):
        pass

    @abstractproperty
    def _value_type(self):
        pass

    @abstractmethod
    def map_first_axis(self, lower, upper):
        pass

    @abstractmethod
    def map_second_axis(self, first_val, lower, upper):
        pass

    @abstractmethod
    def unmap(self):
        pass


class OctahedralGridMap(ABC):
    def __init__(self, base_axis, mapped_axes, resolution):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._value_type = [1.2e0]

    def gauss_first_guess(self):
        i = 0
        gvals = [
            2.4048255577e0,
            5.5200781103e0,
            8.6537279129e0,
            11.7915344391e0,
            14.9309177086e0,
            18.0710639679e0,
            21.2116366299e0,
            24.3524715308e0,
            27.4934791320e0,
            30.6346064684e0,
            33.7758202136e0,
            36.9170983537e0,
            40.0584257646e0,
            43.1997917132e0,
            46.3411883717e0,
            49.4826098974e0,
            52.6240518411e0,
            55.7655107550e0,
            58.9069839261e0,
            62.0484691902e0,
            65.1899648002e0,
            68.3314693299e0,
            71.4729816036e0,
            74.6145006437e0,
            77.7560256304e0,
            80.8975558711e0,
            84.0390907769e0,
            87.1806298436e0,
            90.3221726372e0,
            93.4637187819e0,
            96.6052679510e0,
            99.7468198587e0,
            102.8883742542e0,
            106.0299309165e0,
            109.1714896498e0,
            112.3130502805e0,
            115.4546126537e0,
            118.5961766309e0,
            121.7377420880e0,
            124.8793089132e0,
            128.0208770059e0,
            131.1624462752e0,
            134.3040166383e0,
            137.4455880203e0,
            140.5871603528e0,
            143.7287335737e0,
            146.8703076258e0,
            150.0118824570e0,
            153.1534580192e0,
            156.2950342685e0,
        ]

        numVals = len(gvals)
        vals = []
        for i in range(self._resolution):
            if i < numVals:
                vals.append(gvals[i])
            else:
                vals.append(vals[i - 1] + math.pi)
        return vals

    def first_axis_vals(self):
        precision = 1.0e-14
        nval = self._resolution * 2
        rad2deg = 180 / math.pi
        convval = 1 - ((2 / math.pi) * (2 / math.pi)) * 0.25
        vals = self.gauss_first_guess()
        new_vals = [0] * nval
        denom = math.sqrt(((nval + 0.5) * (nval + 0.5)) + convval)
        for jval in range(self._resolution):
            root = math.cos(vals[jval] / denom)
            conv = 1
            while abs(conv) >= precision:
                mem2 = 1
                mem1 = root
                for legi in range(nval):
                    legfonc = ((2.0 * (legi + 1) - 1.0) * root * mem1 - legi * mem2) / (legi + 1)
                    mem2 = mem1
                    mem1 = legfonc
                conv = legfonc / ((nval * (mem2 - root * legfonc)) / (1.0 - (root * root)))
                root = root - conv
                # add maybe a max iter here to make sure we converge at some point
            new_vals[jval] = math.asin(root) * rad2deg
            new_vals[nval - 1 - jval] = -new_vals[jval]
        return new_vals

    def map_first_axis(self, lower, upper):
        axis_lines = self.first_axis_vals()
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        first_axis_vals = self.first_axis_vals()
        tol = 1e-10
        first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        first_idx = first_axis_vals.index(first_val)
        if first_idx >= self._resolution:
            first_idx = (2 * self._resolution) - 1 - first_idx
        first_idx = first_idx + 1
        npoints = 4 * first_idx + 16
        second_axis_spacing = 360 / npoints
        second_axis_start = 0
        second_axis_vals = [second_axis_start + i * second_axis_spacing for i in range(int(npoints))]
        return second_axis_vals

    def map_second_axis(self, first_val, lower, upper):
        second_axis_vals = self.second_axis_vals(first_val)
        return_vals = [val for val in second_axis_vals if lower <= val <= upper]
        return return_vals

    def axes_idx_to_octahedral_idx(self, first_idx, second_idx):
        octa_idx = 0
        if first_idx == 1:
            octa_idx = second_idx
        else:
            for i in range(first_idx - 1):
                if i <= self._resolution - 1:
                    octa_idx += 16 + 4 * i
                else:
                    i = i - self._resolution + 1
                    if i == 1:
                        octa_idx += 16 + 4 * self._resolution
                    else:
                        i = i - 1
                        octa_idx += 16 + 4 * (self._resolution - i + 1)
            octa_idx += second_idx
        return octa_idx

    def unmap(self, first_val, second_val):
        first_axis_vals = self.first_axis_vals()
        tol = 1e-10
        first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        first_idx = first_axis_vals.index(first_val) + 1
        second_axis_vals = self.second_axis_vals(first_val)
        second_val = [val for val in second_axis_vals if second_val - tol < val < second_val + tol][0]
        second_idx = second_axis_vals.index(second_val)
        octahedral_index = self.axes_idx_to_octahedral_idx(first_idx, second_idx)
        return octahedral_index
