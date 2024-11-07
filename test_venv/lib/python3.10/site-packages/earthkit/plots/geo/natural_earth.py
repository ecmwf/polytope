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

import cartopy.io.shapereader as shpreader

from earthkit.plots.geo.bounds import BoundingBox
from earthkit.plots.utils import string_utils

DEFAULT_CAPITAL_CITIES_KWARGS = {
    "marker": "s",
    "s": 25,
    "color": "darkgrey",
    "edgecolor": "grey",
    "linewidths": 0.5,
    "text": {
        "fontsize": 8,
        "fontweight": "bold",
        "color": "black",
    },
}


DEFAULT_MEDIUM_CITIES_KWARGS = {
    "marker": "o",
    "s": 10,
    "color": "grey",
    "edgecolor": "none",
    "linewidths": 0.5,
    "text": {
        "fontsize": 7,
        "color": "black",
    },
}


DEFAULT_SMALL_CITIES_KWARGS = {
    "marker": "o",
    "s": 6,
    "color": "none",
    "edgecolor": "grey",
    "text": {
        "fontsize": 7,
        "fontstyle": "italic",
        "color": "black",
    },
}


RESOLUTIONS = {
    "low": "110m",
    "medium": "50m",
    "high": "10m",
}


def get_resolution(resolution, ax, crs, max_resolution="high", min_resolution="low"):
    resolutions = list(RESOLUTIONS)
    valid_resolutions = resolutions[
        resolutions.index(min_resolution) : resolutions.index(max_resolution) + 1
    ]
    if resolution is None:
        bbox = BoundingBox(*ax.get_extent(), crs=crs)
        latlon_extents = list(bbox.to_latlon_bbox())
        min_diff = min(
            (latlon_extents[1] - latlon_extents[0]),
            (latlon_extents[3] - latlon_extents[2]),
        )
        if min_diff < 15:
            resolution = "high"
        elif min_diff < 50:
            resolution = "medium"
        else:
            resolution = "low"

    if resolution in RESOLUTIONS:
        if resolutions.index(resolution) < resolutions.index(min_resolution):
            resolution = min_resolution
        elif resolutions.index(resolution) > resolutions.index(max_resolution):
            resolution = max_resolution
        resolution = RESOLUTIONS[resolution]

    if resolution not in RESOLUTIONS.values():
        raise Exception(
            f"urecognised resolution {resolution}; must be one of "
            f"{string_utils.list_to_human(valid_resolutions, conjunction='or')}"
        )
    return resolution


class NaturalEarthDomain:
    """
    Class for building map domains and CRS based on a Natural Earth shape.

    Parameters
    ----------
    domain_name : str
        The name of the domain to be used.
    crs : cartopy.crs.CRS, optional
        The CRS to be used for the domain. If not provided, the CRS will be
        determined from the shapefile.
    """

    NATURAL_EARTH_SOURCES = {
        "admin_0_map_units": "NAME_LONG",
        "admin_0_countries": "NAME_LONG",
        "admin_1_states_provinces": "name_en",
    }

    def __init__(self, domain_name, crs=None):
        self._domain_name = domain_name
        self._record = None
        self._source = None
        self._crs = crs

    @property
    def domain_name(self):
        return self.record.attributes.get(self.NATURAL_EARTH_SOURCES[self._source])

    @property
    def record(self):
        if self._record is None:
            for source, attribute in self.NATURAL_EARTH_SOURCES.items():
                shpfilename = shpreader.natural_earth(
                    resolution="110m", category="cultural", name=source
                )
                reader = shpreader.Reader(shpfilename)
                for record in reader.records():
                    name = record.attributes.get(attribute) or ""
                    name = name.replace("\x00", "")
                    if name.lower() == self._domain_name.lower():
                        break
                else:
                    continue
                break
            else:
                raise ValueError(
                    f"No country or state named '{self._domain_name}' found in "
                    f"Natural Earth's shapefiles"
                )
            self._record = record
            self._source = source

        return self._record

    @property
    def geometry(self):
        return self.record.geometry

    @property
    def crs(self):
        if self._crs is None:
            bounds = BoundingBox.from_geometry(self.geometry)
            self._crs = bounds.to_optimised_bbox().crs

        return self._crs

    @property
    def bounds(self, pad=0.1):
        crs_bounds = list(BoundingBox.from_geometry(self.geometry, target_crs=self.crs))

        if pad:
            x_offset = (crs_bounds[1] - crs_bounds[0]) * pad
            y_offset = (crs_bounds[3] - crs_bounds[2]) * pad
            offset = min(x_offset, y_offset)
            crs_bounds = [
                crs_bounds[0] - offset,
                crs_bounds[1] + offset,
                crs_bounds[2] - offset,
                crs_bounds[3] + offset,
            ]

        return crs_bounds
