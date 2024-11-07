# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import numpy as np

from earthkit.meteo import constants


def speed(u, v):
    r"""Computes the wind speed/vector magnitude.

    Parameters
    ----------
    u: number or ndarray
        u wind/x vector component
    v: number or ndarray
        v wind/y vector component (same units as ``u``)

    Returns
    -------
    number or ndarray
        Wind speed/magnitude (same units as ``u`` and ``v``)

    """
    return np.hypot(u, v)


def _direction_meteo(u, v):
    minus_pi2 = -np.pi / 2.0
    d = np.arctan2(v, u)
    d = np.asarray(d)
    m = d <= minus_pi2
    d[m] = (minus_pi2 - d[m]) * constants.degree
    m = ~m
    d[m] = (1.5 * np.pi - d[m]) * constants.degree
    return d


def _direction_polar(u, v, to_positive):
    d = np.arctan2(v, u) * constants.degree
    if to_positive:
        d = np.asarray(d)
        m = d < 0
        d[m] = 360.0 + d[m]
    return d


def direction(u, v, convention="meteo", to_positive=True):
    r"""Computes the direction/angle of a vector quantity.

    Parameters
    ----------
    u: number or ndarray
        u wind/x vector component
    v: number or ndarray
        v wind/y vector component (same units as ``u``)
    convention: str, optional
        Specifies how the direction/angle is interpreted. The possible values are as follows:

        * "meteo": the direction is the meteorological wind direction (see below for explanation)
        * "polar": the direction is measured anti-clockwise from the x axis (East/right) to the vector

    positive: bool, optional
        If it is True the resulting values are mapped into the [0, 360] range when
        ``convention`` is "polar". Otherwise they lie in the [-180, 180] range.


    Returns
    -------
    number or ndarray
        Direction/angle (degrees)


    The meteorological wind direction is the direction from which the wind is
    blowing. Wind direction increases clockwise such that a northerly wind is 0°, an easterly
    wind is 90°, a southerly wind is 180°, and a westerly wind is 270°. The figure below illustrates
    how it is related to the actual orientation of the wind vector:

    .. image:: /_static/wind_direction.png
        :width: 400px

    """
    if convention == "meteo":
        return _direction_meteo(u, v)
    elif convention == "polar":
        return _direction_polar(u, v, to_positive)
    else:
        raise ValueError(f"direction(): invalid convention={convention}!")


def xy_to_polar(x, y, convention="meteo"):
    r"""Converts wind/vector data from xy representation to polar representation.

    Parameters
    ----------
    x: number or ndarray
        u wind/x vector component
    y: number or ndarray
        v wind/y vector component (same units as ``u``)
    convention: str
        Specifies how the direction/angle component of the target polar coordinate
        system is interpreted. The possible values are as follows:

        * "meteo": the direction is the meteorological wind direction (see :func:`direction` for explanation)
        * "polar": the direction is measured anti-clockwise from the x axis (East/right) to the vector


    Returns
    -------
    number or ndarray
        Magnitude (same units as ``u``)
    number or ndarray
        Direction (degrees)


    In the target xy representation the x axis points East while the y axis points North.

    """
    return speed(x, y), direction(x, y, convention=convention)


def _polar_to_xy_meteo(magnitude, direction):
    a = (270.0 - direction) * constants.radian
    return magnitude * np.cos(a), magnitude * np.sin(a)


def _polar_to_xy_polar(magnitude, direction):
    a = direction * constants.radian
    return magnitude * np.cos(a), magnitude * np.sin(a)


def polar_to_xy(magnitude, direction, convention="meteo"):
    r"""Converts wind/vector data from polar representation to xy representation.

    Parameters
    ----------
    magnitude: number or ndarray
        Speed/magnitude of the vector
    direction: number or ndarray
        Direction of the vector (degrees)
    convention: str
        Specifies how ``direction`` is interpreted. The possible values are as follows:

        * "meteo": ``direction`` is the meteorological wind direction
          (see :func:`direction` for explanation)
        * "polar": ``direction`` is the angle measured anti-clockwise from the x axis
          (East/right) to the vector

    Returns
    -------
    number or ndarray
        X vector component (same units as ``magnitude``)
    number or ndarray
        Y vector component (same units as ``magnitude``)


    In the target xy representation the x axis points East while the y axis points North.

    """
    if convention == "meteo":
        return _polar_to_xy_meteo(magnitude, direction)
    elif convention == "polar":
        return _polar_to_xy_polar(magnitude, direction)
    else:
        raise ValueError(f"polar_to_xy(): invalid convention={convention}!")


def w_from_omega(omega, t, p):
    r"""Computes the hydrostatic vertical velocity from pressure velocity, temperature and pressure.

    Parameters
    ----------
    omega : number or ndarray
        Hydrostatic pressure velocity (Pa/s)
    t : number or ndarray
        Temperature (K)
    p : number or ndarray
        Pressure (Pa)

    Returns
    -------
    number or ndarray
        Hydrostatic vertical velocity (m/s)


    The computation is based on the following hydrostatic formula:

    .. math::

        w = - \frac{\omega\; t R_{d}}{p g}

    where

        * :math:`R_{d}` is the specific gas constant for dry air (see :data:`earthkit.meteo.constants.Rd`).
        * :math:`g` is the gravitational acceleration (see :data:`earthkit.meteo.constants.g`)

    """
    return (-constants.Rd / constants.g) * (omega * t / p)


def coriolis(lat):
    r"""Computes the Coriolis parameter.

    Parameters
    ----------
    lat : number or ndarray
        Latitude (degrees)

    Returns
    -------
    number or ndarray
        The Coriolis parameter (:math:`s^{-1}`)


    The Coriolis parameter is defined by the following formula:

    .. math::

        f = 2 \Omega sin(\phi)

    where :math:`\Omega` is the rotation rate of Earth
    (see :data:`earthkit.meteo.constants.omega`) and :math:`\phi` is the latitude.

    """
    return 2 * constants.omega * np.sin(lat * constants.radian)


def windrose(speed, direction, sectors=16, speed_bins=[], percent=True):
    """Generate windrose data.

    Parameters
    ----------
    speed : number or ndarray
        Speed
    direction : number or ndarray
        Meteorological wind direction (degrees). See :func:`direction` for details.
        Values must be between 0 and 360.
    sectors: number
        Number of sectors the 360 degrees direction range is split into. See below for details.
    speed_bin: list or ndarray
        Speed bins
    percent: bool
        If False, returns the number of valid samples in each bin. If True, returns
        the percentage of the number of samples in each bin with respect to the total
        number of valid samples.


    Returns
    -------
    2d-ndarray
       The bi-dimensional histogram of ``speed`` and ``direction``.  Values in
       ``speed`` are histogrammed along the first dimension and values in ``direction``
       are histogrammed along the second dimension.

    ndarray
        The direction bins (i.e. the sectors) (degrees)


    The sectors do not start at 0 degrees (North) but are shifted by half a sector size.
    E.g. if ``sectors`` is 4 the sectors are defined as:

    .. image:: /_static/wind_sector.png
        :width: 350px

    """
    if len(speed_bins) < 2:
        raise ValueError("windrose(): speed_bins must have at least 2 elements!")

    sectors = int(sectors)
    if sectors < 1:
        raise ValueError("windrose(): sectors must be greater than 1!")

    speed = np.atleast_1d(speed)
    direction = np.atleast_1d(direction)
    dir_step = 360.0 / sectors
    dir_bins = np.linspace(int(-dir_step / 2), int(360 + dir_step / 2), int(360 / dir_step) + 2)

    res = np.histogram2d(speed, direction, bins=[speed_bins, dir_bins], density=False)[0]

    # unify the north bins
    res[:, 0] = res[:, 0] + res[:, -1]
    res = res[:, :-1]
    dir_bins = dir_bins[:-1]

    return ((res * 100.0 / res.sum()) if percent else res), dir_bins
