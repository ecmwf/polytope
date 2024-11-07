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


X = [
    "x",
    "X",
    "xc",
    "projection_x_coordinate",
    "longitude",
    "long",
    "lon",
]

Y = [
    "y",
    "Y",
    "yc",
    "projection_y_coordinate",
    "latitude",
    "lat",
]

LATITUDE = [
    "latitude",
    "lat",
]

LONGITUDE = [
    "longitude",
    "long",
    "lon",
]

TIME = [
    "t",
    "time",
    "valid_time",
    "date",
    "dayofyear",
    "month",
    "year",
]

VARIABLE_NAME_PREFERENCE = [
    "long_name",
    "standard_name",
    "name",
    "short_name",
]


def find(array, identity):
    for candidate in identity:
        if candidate in array:
            return candidate


def find_x(array):
    return find(array, X) or find(array, TIME)


def find_y(array):
    return find(array, Y)


def find_latitude(array):
    return find(array, LATITUDE)


def find_longitude(array):
    return find(array, LONGITUDE)


def find_time(array):
    return find(array, TIME)


def is_regular_latlon(data):
    """Determine whether data is on a regular lat-lon grid."""
    dataset = data.to_xarray().squeeze()
    return all(
        any(name in dataset.dims for name in names) for names in (LATITUDE, LONGITUDE)
    )


def xarray_variable_name(dataset, element=None):
    """
    Get the best long name representing the variable in an xarray Dataset.

    Parameters
    ----------
    dataarray : xarray.Dataset
        The Dataset from which to extract a variable name.
    element : str, optional
        If passed, the variable name for the given element will be extracted.
    """
    if isinstance(element, str):
        da = dataset[element]
        for attr in VARIABLE_NAME_PREFERENCE:
            if attr in da.attrs:
                label = da.attrs[attr]
                break
        else:
            label = element
    else:
        label = list(dataset.data_vars)[0]
    return label
