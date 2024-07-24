# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import numpy as np

from . import constants


def _normalise_lon(lon, minimum):
    while lon < minimum:
        lon += constants.FULL_ANGLE

    while lon >= minimum + constants.FULL_ANGLE:
        lon -= constants.FULL_ANGLE

    return lon


def xyz_to_latlon(x, y, z):
    """Convert from earth-centred, earth-fixed ([ECEF]_) to geodetic coordinates.
    See [From_ECEF_to_geodetic_coordinates]_.

    Parameters
    ----------
    x: float or ndarray
        x-component of the ECEF coordinates.
    y: float or ndarray
        y-component of the ECEF coordinates.
    z: float or ndarray
        z-component of the ECEF coordinates.

    Returns
    -------
    ndarray
        Latitude (degrees).
    ndarray
        Longitude (degrees).


    It is assumed that the Earth is a sphere of radius 1.
    """
    return (
        np.rad2deg(np.arcsin(np.minimum(1.0, np.maximum(-1.0, z)))),
        np.rad2deg(np.arctan2(y, x)),
    )


def latlon_to_xyz(lat, lon):
    """Convert from geodetic to earth-centred, earth-fixed ([ECEF]_) coordinates.
    See [From_geodetic_to_ECEF_coordinates]_.

    Parameters
    ----------
    lat: float or ndarray
        Latitude (degrees).
    lon: float or ndarray
        Longitude (degrees).

    Returns
    -------
    ndarray
        x-component of the ECEF coordinates.
    ndarray
        y-component of the ECEF coordinates.
    ndarray
        z-component of the ECEF coordinates.


    It is assumed that the Earth is a sphere of radius 1. It is also assumed the
    geodetic coordinate h = 0.
    """
    lat = np.asarray(lat)
    lon = np.asarray(lon)
    phi = np.deg2rad(lat)
    lda = np.deg2rad(lon)

    cos_phi = np.cos(phi)
    cos_lda = np.cos(lda)
    sin_phi = np.sin(phi)
    sin_lda = np.sin(lda)

    x = cos_phi * cos_lda
    y = cos_phi * sin_lda
    z = sin_phi

    return x, y, z
