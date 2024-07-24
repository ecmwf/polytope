# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

from . import array


def celsius_to_kelvin(*args, **kwargs):
    return array.celsius_to_kelvin(*args, **kwargs)


def kelvin_to_celsius(*args, **kwargs):
    return array.kelvin_to_celsius(*args, **kwargs)


def specific_humidity_from_mixing_ratio(*args, **kwargs):
    return array.specific_humidity_from_mixing_ratio(*args, **kwargs)


def mixing_ratio_from_specific_humidity(*args, **kwargs):
    return array.mixing_ratio_from_specific_humidity(*args, **kwargs)


def vapour_pressure_from_specific_humidity(*args, **kwargs):
    return array.vapour_pressure_from_specific_humidity(*args, **kwargs)


def vapour_pressure_from_mixing_ratio(*args, **kwargs):
    return array.vapour_pressure_from_mixing_ratio(*args, **kwargs)


def specific_humidity_from_vapour_pressure(*args, **kwargs):
    return array.specific_humidity_from_vapour_pressure(*args, **kwargs)


def mixing_ratio_from_vapour_pressure(*args, **kwargs):
    return array.mixing_ratio_from_vapour_pressure(*args, **kwargs)


def saturation_vapour_pressure(*args, **kwargs):
    return array.saturation_vapour_pressure(*args, **kwargs)


def saturation_mixing_ratio(*args, **kwargs):
    return array.saturation_mixing_ratio(*args, **kwargs)


def saturation_specific_humidity(*args, **kwargs):
    return array.saturation_specific_humidity(*args, **kwargs)


def saturation_vapour_pressure_slope(*args, **kwargs):
    return array.saturation_vapour_pressure_slope(*args, **kwargs)


def saturation_mixing_ratio_slope(*args, **kwargs):
    return array.saturation_mixing_ratio_slope(*args, **kwargs)


def saturation_specific_humidity_slope(*args, **kwargs):
    return array.saturation_specific_humidity_slope(*args, **kwargs)


def temperature_from_saturation_vapour_pressure(*args, **kwargs):
    return array.temperature_from_saturation_vapour_pressure(*args, **kwargs)


def relative_humidity_from_dewpoint(*args, **kwargs):
    return array.relative_humidity_from_dewpoint(*args, **kwargs)


def relative_humidity_from_specific_humidity(*args, **kwargs):
    return array.relative_humidity_from_specific_humidity(*args, **kwargs)


def specific_humidity_from_dewpoint(*args, **kwargs):
    return array.specific_humidity_from_dewpoint(*args, **kwargs)


def mixing_ratio_from_dewpoint(*args, **kwargs):
    return array.mixing_ratio_from_dewpoint(*args, **kwargs)


def specific_humidity_from_relative_humidity(*args, **kwargs):
    return array.specific_humidity_from_relative_humidity(*args, **kwargs)


def dewpoint_from_relative_humidity(*args, **kwargs):
    return array.dewpoint_from_relative_humidity(*args, **kwargs)


def dewpoint_from_specific_humidity(*args, **kwargs):
    return array.dewpoint_from_specific_humidity(*args, **kwargs)


def virtual_temperature(*args, **kwargs):
    return array.virtual_temperature(*args, **kwargs)


def virtual_potential_temperature(*args, **kwargs):
    return array.virtual_potential_temperature(*args, **kwargs)


def potential_temperature(*args, **kwargs):
    return array.potential_temperature(*args, **kwargs)


def temperature_from_potential_temperature(*args, **kwargs):
    return array.temperature_from_potential_temperature(*args, **kwargs)


def pressure_on_dry_adiabat(*args, **kwargs):
    return array.pressure_on_dry_adiabat(*args, **kwargs)


def temperature_on_dry_adiabat(*args, **kwargs):
    return array.temperature_on_dry_adiabat(*args, **kwargs)


def lcl_temperature(*args, **kwargs):
    return array.lcl_temperature(*args, **kwargs)


def lcl(*args, **kwargs):
    return array.lcl(*args, **kwargs)


def ept_from_dewpoint(*args, **kwargs):
    return array.ept_from_dewpoint(*args, **kwargs)


def ept_from_specific_humidity(*args, **kwargs):
    return array.ept_from_specific_humidity(*args, **kwargs)


def saturation_ept(*args, **kwargs):
    return array.saturation_ept(*args, **kwargs)


def temperature_on_moist_adiabat(*args, **kwargs):
    return array.temperature_on_moist_adiabat(*args, **kwargs)


def wet_bulb_temperature_from_dewpoint(*args, **kwargs):
    return array.wet_bulb_temperature_from_dewpoint(*args, **kwargs)


def wet_bulb_temperature_from_specific_humidity(*args, **kwargs):
    return array.wet_bulb_temperature_from_specific_humidity(*args, **kwargs)


def wet_bulb_potential_temperature_from_dewpoint(*args, **kwargs):
    return array.wet_bulb_potential_temperature_from_dewpoint(*args, **kwargs)


def wet_bulb_potential_temperature_from_specific_humidity(*args, **kwargs):
    return array.wet_bulb_potential_temperature_from_specific_humidity(*args, **kwargs)
