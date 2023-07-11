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

    def gauss_first_guess(self):
        i = 0
        gvals = [2.4048255577E0,
                 5.5200781103E0,
                 8.6537279129E0,
                 11.7915344391E0,
                 14.9309177086E0,
                 18.0710639679E0,
                 21.2116366299E0,
                 24.3524715308E0,
                 27.4934791320E0,
                 30.6346064684E0,
                 33.7758202136E0,
                 36.9170983537E0,
                 40.0584257646E0,
                 43.1997917132E0,
                 46.3411883717E0,
                 49.4826098974E0,
                 52.6240518411E0,
                 55.7655107550E0,
                 58.9069839261E0,
                 62.0484691902E0,
                 65.1899648002E0,
                 68.3314693299E0,
                 71.4729816036E0,
                 74.6145006437E0,
                 77.7560256304E0,
                 80.8975558711E0,
                 84.0390907769E0,
                 87.1806298436E0,
                 90.3221726372E0,
                 93.4637187819E0,
                 96.6052679510E0,
                 99.7468198587E0,
                 102.8883742542E0,
                 106.0299309165E0,
                 109.1714896498E0,
                 112.3130502805E0,
                 115.4546126537E0,
                 118.5961766309E0,
                 121.7377420880E0,
                 124.8793089132E0,
                 128.0208770059E0,
                 131.1624462752E0,
                 134.3040166383E0,
                 137.4455880203E0,
                 140.5871603528E0,
                 143.7287335737E0,
                 146.8703076258E0,
                 150.0118824570E0,
                 153.1534580192E0,
                 156.2950342685E0]

        numVals = len(gvals)
        vals = []
        for i in range(self._resolution):
            if i < numVals:
                vals.append(gvals[i])
            else:
                vals.append(vals[i-1] + math.pi)
        return vals

    def first_axis_vals(self):
        precision = 1.0E-14
        nval = self._resolution * 2
        rad2deg = 180/math.pi
        convval = (1-((2/math.pi)*(2/math.pi))*0.25)
        vals = self.gauss_first_guess()
        new_vals = [0]*nval
        denom = math.sqrt(((nval+0.5)*(nval+0.5))+convval)
        for jval in range(self._resolution):
            root = math.cos(vals[jval]/denom)
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
            new_vals[nval-1-jval] = -new_vals[jval]
        return new_vals

    def map_first_axis(self, lower, upper):
        axis_lines = self.first_axis_vals()
        return_vals = [val for val in axis_lines if lower <= val <= upper]
        return return_vals

    def second_axis_vals(self, first_val):
        first_axis_vals = self.first_axis_vals()
        tol = 1E-10
        first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        first_idx = first_axis_vals.index(first_val)
        if first_idx >= self._resolution:
            first_idx = (2*self._resolution) - 1 - first_idx
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
            for i in range(first_idx-1):
                if i <= self._resolution-1:
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
        tol = 1E-10
        first_val = [val for val in first_axis_vals if first_val - tol < val < first_val + tol][0]
        first_idx = first_axis_vals.index(first_val) + 1
        second_axis_vals = self.second_axis_vals(first_val)
        second_val = [val for val in second_axis_vals if second_val - tol < val < second_val + tol][0]
        second_idx = second_axis_vals.index(second_val)
        octahedral_index = self.axes_idx_to_octahedral_idx(first_idx, second_idx)
        return octahedral_index
