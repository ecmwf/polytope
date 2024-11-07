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

import re


def list_to_human(iterable, conjunction="and", oxford_comma=False):
    """
    Convert an iterable to a human-readable string.

    Parameters
    ----------
    iterable : list or tuple
        The list of strings to convert to a single natural language string.
    conjunction : str, optional
        The conjunction with which to join the last two elements of the list,
        for example "and" (default).
    oxford_comma : bool, optional
        If `True`, an "Oxford comma" will be added before the conjunction when
        there are three or more elements in the list. Default is `False`.

    Returns
    -------
    str

    Example
    -------
    >>> list_to_human(["sausage", "egg", "chips"])
    'sausage, egg and chips'
    """
    list_of_strs = [str(item) for item in iterable]

    if len(list_of_strs) > 2:
        list_of_strs = [", ".join(list_of_strs[:-1]), list_of_strs[-1]]
        if oxford_comma:
            list_of_strs[0] += ","

    return f" {conjunction} ".join(list_of_strs)


def split_camel_case(string):
    """
    Split a CamelCase string into its constituent words.

    Parameters
    ----------
    string : str
        The string to split by camel case words.

    Returns
    -------
    list

    Example
    -------
    >>> split_camel_case("ACamelCaseString")
    ['A', 'Camel', 'Case', 'String']
    """
    matches = re.finditer(
        ".+?(?:(?<=[a-z])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])|$)",
        string,
    )
    return [m.group(0) for m in matches]
