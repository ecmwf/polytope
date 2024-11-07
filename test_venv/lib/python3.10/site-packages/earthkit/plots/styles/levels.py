# Copyright 2023, European Centre for Medium Range Weather Forecasts.
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

import numpy as np

from earthkit.plots.schemas import schema


def auto_range(data, divergence_point=None, n_levels=schema.default_style_levels):
    """
    Attempt to generate a suitable range of levels for arbitrary input data.

    NOTE: **Experimental!**

    Parameters
    ----------
    data : numpy.ndarray or xarray.DataArray or earthkit.data.core.Base
        The data for which to generate a list of levels.
    divergence_point : float, optional
        If provided, force the levels to be centred on this point. This is
        mostly useful for parameters which use diverging colors in their style,
        such as anomalies.
    n_levels : int, optional
        The number of levels to generate.

    Returns
    -------
    list
    """
    try:
        data = data.to_numpy()
    except AttributeError:
        pass

    min_value = np.nanmin(data)
    max_value = np.nanmax(data)

    if divergence_point is not None:
        max_diff = max(max_value - divergence_point, divergence_point - min_value)
        max_value = max_diff
        min_value = -max_diff

    data_range = max_value - min_value

    initial_bin = data_range / n_levels

    magnitude = 10 ** (np.floor(np.log10(initial_bin)))
    bin_width = initial_bin - (initial_bin % -magnitude)

    min_value -= min_value % bin_width
    max_value -= max_value % -bin_width

    if divergence_point is not None:
        min_value += divergence_point
        max_value += divergence_point

    return np.linspace(
        min_value,
        max_value,
        n_levels + 1,
    ).tolist()


def step_range(data, step, reference=None):
    """
    Generate a range of levels for some data based on a level step and multiple.

    Parameters
    ----------
    data : numpy.ndarray or xarray.DataArray or earthkit.data.core.Base
        The data for which to generate a list of levels.
    step : float
        The step/difference between each level in the desired level range.
    reference : float, optional
        The reference point around which to calibrate the level range. For
        example, if a `step` of 4 is used and a `reference` of 2 is used, then
        the generated levels will be generated as steps of 4 above and below
        the number 2.

    Returns
    -------
    list
    """
    try:
        data = data.to_numpy()
    except AttributeError:
        pass

    if reference is None:
        reference = step

    min_value = np.nanmin(data)
    max_value = np.nanmax(data)

    max_modifier = reference % step
    min_modifier = max_modifier if max_modifier == 0 else step - max_modifier

    min_value = min_value - (min_value % step) - min_modifier

    levels = np.arange(min_value, max_value + step, step).tolist()
    if levels[1] <= np.nanmin(data):
        levels = levels[1:]

    return levels


class Levels:
    """
    Class defining levels to use with a mapping style.

    Parameters
    ----------
    levels : list, optional
        A static list of levels to always use, no matter the input data.
    step : float, optional
        The step/difference between each level in the desired level range.
    reference : float, optional
        The reference point around which to calibrate the level range. For
        example, if a `step` of 4 is used and a `reference` of 2 is used, then
        the generated levels will be generated as steps of 4 above and below
        the number 2.
    divergence_point : float, optional
        If provided, force the levels to be centred on this point. This is
        mostly useful for parameters which use diverging colors in their style,
        such as anomalies.
    """

    @classmethod
    def from_config(cls, config):
        if isinstance(config, str):
            if config.startswith("range"):
                args = (
                    int(i)
                    for i in config.replace("range(", "").replace(")", "").split(",")
                )
                kwargs = {"levels": range(*args)}
        elif isinstance(config, dict):
            kwargs = config
        else:
            kwargs = {"levels": config}
        return cls(**kwargs)

    def __eq__(self, other):
        if self._levels is not None and other is not None:
            return self._levels == other._levels
        else:
            return False

    def __init__(
        self,
        levels=None,
        step=None,
        reference=None,
        divergence_point=None,
    ):
        self._levels = levels
        self._step = step
        self._reference = reference
        self._divergence_point = divergence_point

    def apply(self, data):
        """
        Generate levels specific to some data.

        Parameters
        ----------
        data : numpy.ndarray or xarray.DataArray or earthkit.data.core.Base
            The data for which to generate a list of levels.

        Returns
        -------
        list
        """
        if self._levels is None:
            if self._step is None:
                return auto_range(data, self._divergence_point)
            else:
                return step_range(data, self._step, self._reference)
        return self._levels
