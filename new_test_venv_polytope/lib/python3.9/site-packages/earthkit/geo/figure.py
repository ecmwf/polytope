# (C) Copyright 2024 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


class Figure:
    """Figure representing the size and shape of a spheroid"""

    pass


class Sphere(Figure):
    """Base class for a sphere. The radius is in metres."""

    def __init__(self, radius):
        self._radius = radius
        if self._radius <= 0.0:
            raise ValueError(f"Radius={self._radius} must be positive")

    @property
    def radius(self):
        return self._radius

    def scale(self, *args):
        if len(args) > 1:
            return tuple([x * self.radius for x in args])
        else:
            return args[0] * self.radius


class UnitSphere(Sphere):
    """Unit sphere (with the radius of 1 m)."""

    def __init__(self):
        super().__init__(1.0)

    def scale(self, *args):
        if len(args) > 1:
            return args
        else:
            return args[0]


IFS_SPHERE = Sphere(6371229.0)
r"""Object of spherical Earth with radius=6371229 m as used in the IFS.
See [IFS-CY47R3-PhysicalProcesses]_ (Chapter 12)."""

UNIT_SPHERE = UnitSphere()
r"""Object of unit sphere (with the radius of 1 m)."""
