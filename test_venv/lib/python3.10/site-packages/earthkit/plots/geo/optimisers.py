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

import inspect

import cartopy.crs as ccrs

GLOBE_AREA = 64800  # 360*180


class OptimisedCRS:
    """
    Base class for optimised cartopy CRS classes.
    """

    def to_ccrs(self, optimiser):
        return getattr(ccrs, self.cartopy_crs())(**self.get_kwargs(optimiser))

    def get_kwargs(self, optimiser):
        attributes = inspect.getmembers(
            self.__class__, lambda attr: not (inspect.isroutine(attr))
        )
        attributes = [
            attr
            for attr in attributes
            if not (attr[0].startswith("__") and attr[0].endswith("__"))
        ]
        return {attr[0].lower(): getattr(optimiser, attr[1]) for attr in attributes}

    def cartopy_crs(self):
        return self.__class__.__name__


class PlateCarree(OptimisedCRS):
    CENTRAL_LONGITUDE = "central_lon"


class LambertAzimuthalEqualArea(OptimisedCRS):
    CENTRAL_LATITUDE = "central_lat"
    CENTRAL_LONGITUDE = "central_lon"


class TransverseMercator(OptimisedCRS):
    CENTRAL_LATITUDE = "central_lat"
    CENTRAL_LONGITUDE = "central_lon"


class AlbersEqualArea(OptimisedCRS):
    CENTRAL_LATITUDE = "central_lat"
    CENTRAL_LONGITUDE = "central_lon"
    STANDARD_PARALLELS = "standard_parallels"


class NorthPolarStereo(OptimisedCRS):
    CENTRAL_LONGITUDE = "central_lon"


class SouthPolarStereo(OptimisedCRS):
    CENTRAL_LONGITUDE = "central_lon"


class CRSOptimiser:
    """
    Base class for optimising cartopy CRS classes based on domain extents.

    Parameters
    ----------
    extents : list
        The domain extents in the form [min_lon, max_lon, min_lat, max_lat].
    small_threshold : float, optional
        The threshold for a small domain as a fraction of the globe's area.
    large_threshold : float, optional
        The threshold for a large domain as a fraction of the globe's area.
    """

    CRS = PlateCarree

    def __init__(self, extents, small_threshold=0.2, large_threshold=0.6):
        self.extents = list(extents)
        self.small_threshold = small_threshold * GLOBE_AREA
        self.large_threshold = large_threshold * GLOBE_AREA

    @property
    def area(self):
        """The area of the domain in square degrees."""
        if self.max_lat == self.min_lat:
            multiplicator = 2 * (90 - abs(self.max_lat))
        else:
            multiplicator = self.max_lat - self.min_lat

        return (self.max_lon - self.min_lon) * multiplicator

    @property
    def ratio(self):
        """The aspect ratio of the domain."""
        if self.min_lat == self.max_lat:
            denominator = 2 * (90 - abs(self.max_lat))
        else:
            denominator = self.max_lat - self.min_lat
        return (self.max_lon - self.min_lon) / denominator

    @property
    def standard_parallels(self):
        """The standard parallels for the projection."""
        offset = (self.max_lat - self.min_lat) * (4 / 25)
        return (self.min_lat + offset, self.max_lat - offset)

    @property
    def min_lon(self):
        """The minimum longitude of the domain."""
        return self.extents[0]

    @property
    def max_lon(self):
        """The maximum longitude of the domain."""
        value = self.extents[1]
        if value < self.min_lon:
            value = 180 + (180 + value)
        return value

    @property
    def min_lat(self):
        """The minimum latitude of the domain."""
        return self.extents[2]

    @property
    def max_lat(self):
        """The maximum latitude of the domain."""
        return self.extents[3]

    @property
    def central_lat(self):
        """The central latitude of the domain."""
        return self.max_lat - (self.max_lat - self.min_lat) / 2

    @property
    def central_lon(self):
        """The central longitude of the domain."""
        return self.max_lon - (self.max_lon - self.min_lon) / 2

    def is_landscape(self):
        """Landscape domains are at leadt 20% wider than they are tall."""
        return self.ratio > 1.2

    def is_portrait(self):
        """Portrait domains are at least 20% taller than they are wide."""
        return self.ratio < 0.8

    def is_square(self):
        """Square domains have a width and height within 20% of each other."""
        return not self.is_landscape() and not self.is_portrait()

    def is_global(self):
        """Global domains cover > 60% of the globe."""
        return self.area > self.large_threshold

    def is_large(self):
        """Large domains cover < 60% of the globe but > 20%."""
        return not self.is_global() and self.area > self.small_threshold

    def is_small(self):
        """Small domains cover < 20% of the globe."""
        return not self.is_global() and not self.is_large()

    def is_polar(self):
        """Polar domains are centered around a pole."""
        return abs(self.central_lat) > 75

    def is_equatorial(self):
        """Equatorial domains are centered around the equator."""
        return abs(self.central_lat) < 25

    def mutate(self):
        """Mutate the domain to a more optimal CRS."""
        return self

    @property
    def crs(self):
        """The cartopy CRS for the domain."""
        return self.CRS().to_ccrs(self)


class Global(CRSOptimiser):
    """A domain which covers >60% of the globe."""

    CRS = PlateCarree

    def mutate(self):
        """Mutate the domain to a more optimal CRS."""
        if not self.is_global():
            return Equatorial(self.extents)
        return self


class Equatorial(CRSOptimiser):
    """A domain with a central longitude < ±25 degrees, covering < 20% of the globe."""

    CRS = PlateCarree

    def mutate(self):
        """Mutate the domain to a more optimal CRS."""
        if not self.is_equatorial():
            if self.is_polar():
                return NorthPolar(self.extents)
            else:
                return Square(self.extents)
        elif self.is_large():
            return LargeEqatorial(self.extents)
        return self


class NorthPolar(CRSOptimiser):
    """A domain with a central longitude > 75 degrees."""

    CRS = NorthPolarStereo

    def mutate(self):
        """Mutate the domain to a more optimal CRS."""
        if self.central_lat < 0:
            return SouthPolar(self.extents)
        return self


class SouthPolar(CRSOptimiser):
    """A domain with a central longitude < -75 degrees."""

    CRS = SouthPolarStereo


class LargeEqatorial(CRSOptimiser):
    """A domain with a central longitude < ±25 degrees, covering > 20% of the globe."""

    CRS = PlateCarree


class Square(CRSOptimiser):
    """A non-equitorial domain with an aspect ratio > 0.8 and < 1.2."""

    CRS = AlbersEqualArea

    def mutate(self):
        """Mutate the domain to a more optimal CRS."""
        if self.is_landscape():
            return Landscape(self.extents)
        elif self.is_portrait():
            return Portrait(self.extents)
        return self


class Landscape(CRSOptimiser):
    """A non-equitorial domain with an aspect ratio > 1.2."""

    CRS = AlbersEqualArea


class Portrait(CRSOptimiser):
    """A non-equitorial domain with an aspect ratio < 0.8."""

    CRS = PlateCarree
