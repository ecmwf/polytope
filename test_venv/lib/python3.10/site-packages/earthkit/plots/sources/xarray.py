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
import pandas as pd

from earthkit.plots import identifiers
from earthkit.plots.sources.single import SingleSource


class XarraySource(SingleSource):
    """
    Source class for xarray data.

    Parameters
    ----------
    data : xarray.Dataset
        The data to be plotted.
    x : str, optional
        The x-coordinate variable in data.
    y : str, optional
        The y-coordinate variable in data.
    z : str, optional
        The z-coordinate variable in data.
    u : str, optional
        The u-component variable in data.
    v : str, optional
        The v-component variable in data.
    crs : cartopy.crs.CRS, optional
        The CRS of the data.
    **kwargs
        Metadata keys and values to attach to this Source.
    """

    @cached_property
    def data(self):
        """The underlying xarray data."""
        return self._data.squeeze()

    @property
    def coordinate_axis(self):
        """The coordinate axis of the data. One of 'x' or 'y'."""
        if self._x in self.data.dims:
            return "x"
        else:
            return "y"

    def metadata(self, key, default=None):
        """
        Extract metadata from the data.

        Parameters
        ----------
        key : str
            The metadata key to extract.
        default : any, optional
            The default value to return if the key is not found.
        """
        value = super().metadata(key, default)
        if value == default:
            if key in self.data.attrs:
                value = self.data.attrs[key]
            elif hasattr(self.data, key):
                value = getattr(self.data, key)
            elif self._z and hasattr(self.data[self._z], key):
                value = getattr(self.data[self._z], key)
            if hasattr(value, "values"):
                value = value.values
        return value

    def datetime(self):
        """Get the datetime of the data."""
        datetimes = [
            pd.to_datetime(dt).to_pydatetime()
            for dt in np.atleast_1d(self.data.time.values)
        ]
        return {
            "base_time": datetimes,
            "valid_time": datetimes,
        }

    def extract_xyz(self):
        """Extract the x, y and z values from the data."""
        x, y, z = self._x, self._y, self._z
        if self._x is None and self._y is None and self._z is None:
            x, y = self.extract_xy()
            z = None
            if hasattr(self.data, "data_vars"):
                for z in list(self.data.data_vars):
                    if set(self.data[z].dims) == set(self.dims):
                        break
                else:
                    z = None
        return x, y, z

    @cached_property
    def dims(self):
        """The dimensions of the data."""
        return list(self.data.dims)

    def extract_xy(self):
        """Extract the x and y values from the data."""
        x = self._x or identifiers.find_x(self.dims)
        y = self._y or identifiers.find_y(self.dims)

        if (x is not None and x == y) or (x is None and y is not None):
            if self._x is not None:
                x = self._x
                y = None
            else:
                x = [dim for dim in self.dims if dim != y][0]

        if x is None:
            if len(self.dims) == 2:
                y, x = self.dims
            else:
                x = self.dims[0]

        if y is None:
            y = [dim for dim in self.dims if dim != x][0]

        return x, y

    def extract_x(self):
        """Extract the x values of the data."""
        return self.extract_xy()[0]

    def extract_y(self):
        """Extract the y values of the data."""
        return self.extract_xy()[1]

    def extract_z(self):
        """Extract the z values of the data."""
        z = super().extract_z()
        return z

    def extract_u(self):
        """Extract the u values of the data."""
        if self._u is None:
            self._u = "u10"
        return self._u

    def extract_v(self):
        """Extract the v values of the data."""
        if self._v is None:
            self._v = "v10"
        return self._v

    @property
    def crs(self):
        """The CRS of the data."""
        if self._crs is None:
            earthkit_data = self.to_earthkit()
            try:
                self._crs = earthkit_data.projection().to_cartopy_crs()
            except ValueError:
                try:
                    self._crs = earthkit_data[0].projection().to_cartopy_crs()
                except (AttributeError, NotImplementedError):
                    self._crs = None
            except (AttributeError, NotImplementedError):
                self._crs = None
        return self._crs

    @property
    def x_values(self):
        """The x values of the data."""
        super().x_values
        return self.data[self._x].values

    @cached_property
    def y_values(self):
        """The y values of the data."""
        super().y_values
        return self.data[self._y].values

    @cached_property
    def z_values(self):
        """The z values of the data."""
        values = None
        if self._z is None:
            if not hasattr(self.data, "data_vars"):
                data = self.data
            else:
                data = self.data[list(self.data.data_vars)[0]]
        else:
            data = self.data[self._z]
        values = data.values
        # x, y = self.extract_xy()
        # if [y, x] != [c for c in data.dims if c in [y, x]]:
        #     values = values.T

        return values

    @cached_property
    def u_values(self):
        """The u values of the data."""
        self.extract_u()
        return self.data[self._u].values.squeeze()

    @cached_property
    def v_values(self):
        """The v values of the data."""
        self.extract_v()
        return self.data[self._v].values.squeeze()

    @cached_property
    def magnitude_values(self):
        """The magnitude values of the data."""
        return (self.u_values**2 + self.v_values**2) ** 0.5
