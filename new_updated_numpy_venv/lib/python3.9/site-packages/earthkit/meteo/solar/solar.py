# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

from . import array


def julian_day(*args, **kwargs):
    return array.julian_day(*args, **kwargs)


def solar_declination_angle(*args, **kwargs):
    return array.solar_declination_angle(*args, **kwargs)


def cos_solar_zenith_angle(*args, **kwargs):
    return array.cos_solar_zenith_angle(*args, **kwargs)


def cos_solar_zenith_angle_integrated(*args, **kwargs):
    return array.cos_solar_zenith_angle_integrated(*args, **kwargs)


def incoming_solar_radiation(*args, **kwargs):
    return array.incoming_solar_radiation(*args, **kwargs)


def toa_incident_solar_radiation(*args, **kwargs):
    return array.toa_incident_solar_radiation(*args, **kwargs)
