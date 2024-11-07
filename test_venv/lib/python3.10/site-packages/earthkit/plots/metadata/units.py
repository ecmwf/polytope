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

from pint import UnitRegistry

ureg = UnitRegistry()
Q_ = ureg.Quantity


def _pintify(unit_str):
    # Replace spaces with dots
    unit_str = unit_str.replace(" ", ".")

    # Insert ^ between characters and numbers (including negative numbers)
    unit_str = re.sub(r"([a-zA-Z])(-?\d+)", r"\1^\2", unit_str)

    return ureg(unit_str).units


#: Units for temperature anomalies.
TEMPERATURE_ANOM_UNITS = [
    "kelvin",
    "celsius",
]


#: Unit equivalences.
UNIT_EQUIVALENCE = {
    "kg m-2": "mm",
}


def are_equal(unit_1, unit_2):
    """
    Check if two units are equivalent.

    Parameters
    ----------
    unit_1 : str
        The first unit.
    unit_2 : str
        The second unit.
    """
    return _pintify(unit_1) == _pintify(unit_2)


def anomaly_equivalence(units):
    """
    Check if units are equivalent for temperature anomalies.

    This is a special case for temperature anomalies, for which Kelvin and
    Celsius are considered equivalent.

    Parameters
    ----------
    units : str
        The units to check for equivalence.
    """
    return any(are_equal(units, t_units) for t_units in TEMPERATURE_ANOM_UNITS)


def convert(data, source_units, target_units):
    """
    Convert data from one set of units to another.

    Parameters
    ----------
    data : numpy.ndarray
        The data to convert.
    source_units : str
        The units of the data.
    target_units : str
        The units to convert to.
    """
    source_units = _pintify(source_units)
    target_units = _pintify(target_units)
    try:
        result = (data * source_units).to(target_units).magnitude
    except ValueError as err:
        for units in UNIT_EQUIVALENCE:
            if source_units == _pintify(units):
                try:
                    equal_units = _pintify(UNIT_EQUIVALENCE[units])
                    result = (data * equal_units).to(target_units)
                except ValueError:
                    raise err
                else:
                    break
    return result


def format_units(units, exponential_notation=False):
    """
    Format units for display in LaTeX.

    Parameters
    ----------
    units : str
        The units to format.

    Example
    -------
    >>> format_units("kg m-2")
    "$kg m^{-2}$"
    """
    units = _pintify(units)
    if units.dimensionless:
        return "dimensionless"
    latex_str = f"{units:~L}"
    if exponential_notation:
        raise NotImplementedError("Exponential notation is not yet supported.")
    return f"${latex_str}$"
