# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

from . import constants
from .coord import _normalise_lon, latlon_to_xyz, xyz_to_latlon


def _normalise(x):
    return max(min(x, 1.0), -1.0)


def _rotation_matrix(south_pole_lat, south_pole_lon):
    """
    Define matrix for spherical rotation.
    """
    import numpy as np

    theta = -np.deg2rad(south_pole_lat - constants.SOUTH_POLE_LAT)
    phi = -np.deg2rad(south_pole_lon)

    ct = np.cos(theta)
    st = np.sin(theta)
    cp = np.cos(phi)
    sp = np.sin(phi)

    return np.array([[cp * ct, sp, cp * st], [-ct * sp, cp, -sp * st], [-st, 0.0, ct]])


def rotate(lat, lon, south_pole_lat, south_pole_lon):
    """
    Rotate geographical coordinates on a sphere.

    Parameters
    ----------
    lat: ndarray
        Latitudes (degrees).
    lon: ndarray
        Longitudes (degrees).
    south_pole_lat: float
        Latitude of the rotated south pole (degrees).
    south_pole_lon: float
        Longitude of the rotated south pole (degrees).

    Returns
    -------
    ndarray
        Rotated latitudes (degrees).
    ndarray
        Rotated longitudes (degrees).


    The rotation is specified by the position
    where the south pole is rotated to, i.e. by (``south_pole_lat``, ``south_pole_lon``).


    See Also
    --------
    :obj:`unrotate`

    Examples
    --------
    >>> from earthkit.geo.rotate import rotate
    >>> lat = [-90]
    >>> lon = [0]
    >>> south_pole_lat = -20
    >>> south_pole_lon = -40
    >>> rotate(lat, lon, south_pole_lat, south_pole_lon)
    (array([-20.]), array([-40.]))

    For more examples, see:
        - :ref:`/examples/rotate.ipynb`

    """
    import numpy as np

    matrix = _rotation_matrix(south_pole_lat, south_pole_lon)
    return xyz_to_latlon(*np.dot(matrix, latlon_to_xyz(lat, lon)))


def unrotate(lat, lon, south_pole_lat, south_pole_lon):
    """
    Unrotate geographical coordinates on a sphere.

    Parameters
    ----------
    lat: ndarray
        Latitudes of the rotated points (degrees).
    lon: ndarray
        Longitudes of the rotated points (degrees).
    south_pole_lat: float
        Latitude of the rotated south pole (degrees).
    south_pole_lon: float
        Longitude of the rotated south pole (degrees).

    Returns
    -------
    ndarray
        Unrotated latitudes (degrees).
    ndarray
        Unrotated longitudes (degrees).


    :func:`unrotate` operates on points already rotated with a rotation specified
    by (``south_pole_lat``, ``south_pole_lon``). The function rotates the points
    back to the original locations.

    See Also
    --------
    :obj:`rotate`

    Examples
    --------
    >>> from earthkit.geo.rotate import unrotate
    >>> lat = [-18]
    >>> lon = [-41]
    >>> south_pole_lat = -20
    >>> south_pole_lon = -40
    >>> unrotate(lat, lon, south_pole_lat, south_pole_lon)
    (array([-87.78778846]), array([-25.4673765]))
    """
    import numpy as np

    matrix = _rotation_matrix(south_pole_lat, south_pole_lon)
    matrix = matrix.T
    return xyz_to_latlon(*np.dot(matrix, latlon_to_xyz(lat, lon)))


def rotate_vector(lat, lon, vector_x, vector_y, source_projection, target_projection):
    """Rotate vectors from source to target projection coordinates.

    Parameters
    ----------
    lat: ndarray
        Latitude coordinates of the points (degrees).
    lon: ndarray
        Longitude coordinates of the points (degrees).
    vector_x: ndarray
        x component of the vector in the source projection.
    vector_y: ndarray
        y component of the vector in the source projection.
    source_projection: str, dict
        Projection that the vector components are defined in. It is either a proj string
        or a dict of map projection control parameter key/value pairs. Passed to pyproj.Proj().
    target_projection: str, dict
        Projection that the vector components should be transformed to. It is either a proj string
        or a dict of map projection control parameter key/value pairs. Passed to pyproj.Proj().

    Returns
    -------
    ndarray
        x component of the vector in the target projection.
    ndarray
        y component of the vector in the target projection).


    The vector is returned at the same locations (``lat``, ``lon``), but rotated
    into ``target_projection`` coordinates. The magnitude of the vector is preserved.

    Based on code from MET Norway.
    """
    import numpy as np
    import pyproj

    if source_projection == target_projection:
        return vector_x, vector_y

    source_projection = pyproj.Proj(source_projection)
    target_projection = pyproj.Proj(target_projection)

    transformer = pyproj.transformer.Transformer.from_proj(
        source_projection, target_projection
    )

    # To compute the new vector components:
    # 1) perturb each position in the direction of the vectors
    # 2) convert the perturbed positions into the new coordinate system
    # 3) measure the new x/y components.
    #
    # A complication occurs when using the longlat "projections", since this is not a cartesian grid
    # (i.e. distances in each direction is not consistent), we need to deal with the fact that the
    # width of a longitude varies with latitude
    orig_magn = np.sqrt(vector_x**2 + vector_y**2)

    x0, y0 = source_projection(lon, lat)

    if source_projection.name != "longlat":
        x1 = x0 + vector_x
        y1 = y0 + vector_y
    else:
        # Reduce the perturbation, since vector_x and vector_y are in meters, which
        # would create large perturbations in lat, lon. Also, deal with the fact that the
        # width of longitude varies with latitude.
        factor = 3600000.0
        x1 = x0 + vector_x / factor / np.cos(np.deg2rad(lat))
        y1 = y0 + vector_y / factor

    X0, Y0 = transformer.transform(x0, y0)
    X1, Y1 = transformer.transform(x1, y1)

    new_vector_x = X1 - X0
    new_vector_y = Y1 - Y0
    if target_projection.name == "longlat":
        new_vector_x *= np.cos(np.deg2rad(lat))

    if target_projection.name == "longlat" or source_projection.name == "longlat":
        # Ensure the vector magnitude not changed (which might not be the case since the
        # units in longlat is degrees, not meters)
        curr_magn = np.sqrt(new_vector_x**2 + new_vector_y**2)
        new_vector_x *= orig_magn / curr_magn
        new_vector_y *= orig_magn / curr_magn

    return new_vector_x, new_vector_y


def unrotate_vector(
    lat,
    lon,
    vector_x,
    vector_y,
    south_pole_lat,
    south_pole_lon,
    south_pole_rotation_angle=0,
    lat_unrotated=None,
    lon_unrotated=None,
):
    """
    Rotate vectors on a rotated grid back into eastward and northward components.

    Parameters
    ----------
    lat: ndarray
        Latitude coordinates of the rotated points (degrees).
    lon: ndarray
        Longitude coordinates of the rotated points (degrees).
    vector_x: ndarray
        x vector component in the rotated
        coordinate system at the rotated points.
    vector_y: ndarray
        y vector component in the rotated
        coordinate system at the rotated points.
    south_pole_lat: float
        Latitude of the south pole defining the rotation (degrees).
    south_pole_lon: float
        Longitude of the south pole defining the rotation (degrees).
    south_pole_rotation_angle: float, optional
        Rotation angle around the south pole (degrees). Currently not supported.
    lat_unrotated: ndarray, optional
        Latitude coordinates of the points before rotation (degrees).
    lon_unrotated: ndarray, optional
        Longitude coordinates of the points before rotation (degrees).

    Returns
    -------
    ndarray
        x component of the vector rotated back to
        eastward and northward components.
    ndarray
        y component of the vector rotated back to
        eastward and northward components.


    Use this method when a grid is rotated spherically and the vector components are
    locally rotated at each target grid point into the new local (rotated) coordinate
    system. :func:`unrotate_vector` performs the inverse operation, and rotates back the
    vectors to their original directions at each point. The vector is returned at
    the same locations (``lat``, ``lon``) and its magnitude is preserved.

    """
    import numpy as np

    assert south_pole_rotation_angle == 0

    C = np.deg2rad(constants.NORTH_POLE_LAT - south_pole_lat)
    cos_C = np.cos(C)
    sin_C = np.sin(C)

    new_x = np.zeros_like(vector_x)
    new_y = np.zeros_like(vector_y)

    if lon_unrotated is None:
        _, lon_unrotated = unrotate(lat, lon, south_pole_lat, south_pole_lon)

    for i, (vx, vy, lon_r, lon_ur) in enumerate(
        zip(vector_x, vector_y, lon, lon_unrotated)
    ):
        lon_r = south_pole_lon - lon_r
        lon_r = _normalise_lon(lon_r, -constants.STRAIGHT_ANGLE)

        a = np.deg2rad(lon_r)
        b = np.deg2rad(lon_ur)
        q = 1.0 if (sin_C * lon_r < 0.0) else -1.0  # correct quadrant

        cos_c = _normalise(np.cos(a) * np.cos(b) + np.sin(a) * np.sin(b) * cos_C)
        sin_c = q * np.sqrt(1.0 - cos_c * cos_c)

        new_x[i] = cos_c * vx + sin_c * vy
        new_y[i] = -sin_c * vx + cos_c * vy

    return new_x, new_y
