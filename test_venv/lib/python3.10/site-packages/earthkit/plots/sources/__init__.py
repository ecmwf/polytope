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

import earthkit.data as ek_data

from earthkit.plots.sources.earthkit import EarthkitSource
from earthkit.plots.sources.numpy import NumpySource
from earthkit.plots.sources.xarray import XarraySource


def get_source(*args, data=None, x=None, y=None, z=None, u=None, v=None, **kwargs):
    """
    Get a Source object from the given data.

    Parameters
    ----------
    *args
        The positional arguments to pass to the Source constructor.
    data : numpy.ndarray, xarray.DataArray, earthkit.data.core.Base, optional
        The data to be plotted.
    x : numpy.ndarray or str, optional
        The x-coordinates of the data. If a string, it is assumed to be the name
        of the x-coordinate variable in data.
    y : numpy.ndarray or str, optional
        The y-coordinates of the data. If a string, it is assumed to be the name
        of the y-coordinate variable in data.
    z : numpy.ndarray or str, optional
        The z-coordinates of the data. If a string, it is assumed to be the name
        of the z-coordinate variable in data.
    u : numpy.ndarray or str, optional
        The u-component of the data. If a string, it is assumed to be the name
        of the u-component variable in data.
    v : numpy.ndarray or str, optional
        The v-component of the data. If a string, it is assumed to be the name
        of the v-component variable in data.
    **kwargs
        Additional keyword arguments to pass to the Source constructor.
    """
    cls = NumpySource
    core_data = data
    if len(args) == 1 and core_data is None:
        core_data = args[0]
    if core_data is not None:
        if core_data.__class__.__name__ in ("Dataset", "DataArray"):
            cls = XarraySource
        elif isinstance(core_data, ek_data.core.Base):
            cls = EarthkitSource
    return cls(*args, data=data, x=x, y=y, z=z, u=u, v=v, **kwargs)
