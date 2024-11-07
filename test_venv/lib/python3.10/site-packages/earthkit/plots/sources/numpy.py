# Copyright 2024, European Centre for Medium Range Weather Forecasts.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from functools import cached_property

import numpy as np

from earthkit.plots.sources.single import SingleSource


class NumpySource(SingleSource):
    """
    Source class for numpy data.

    Parameters
    ----------
    data : numpy.ndarray
        The data to be plotted.
    x : numpy.ndarray, optional
        The x-coordinates of the data.
    y : numpy.ndarray, optional
        The y-coordinates of the data.
    z : numpy.ndarray, optional
        The z-coordinates of the data.
    """

    @cached_property
    def data(self):
        if self._data is not None:
            self._data = np.array(self._data)
        return self._data

    def extract_xyz(self):
        xyz = self._x, self._y, self._z
        if self._x is None and self._y is None and self._z is None:
            if len(self.data.shape) == 1:
                xyz = np.arange(len(self.data)), self.data, None
            elif len(self.data.shape) == 2:
                xyz = np.arange(len(self.data[0])), np.arange(len(self.data)), self.data
        return xyz

    def extract_x(self):
        x = super().extract_x()
        if self._data is not None:
            x = np.arange(self.data.shape[1])
        else:
            if self._z is None:
                x = np.arange(len(self._y))
            else:
                x = np.arange(self.z_values.shape[1])
        return x

    def extract_y(self):
        y = super().extract_y()
        if self._data is not None:
            y = np.arange(self.data.shape[0])
        else:
            if self._z is None:
                y = np.arange(len(self._x))
            else:
                y = np.arange(self.z_values.shape[0])
        return y

    def extract_z(self):
        z = super().extract_z()
        if z is not None:
            z = np.array(z)
        return z
