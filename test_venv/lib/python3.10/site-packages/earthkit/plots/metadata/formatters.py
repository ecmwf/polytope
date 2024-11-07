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

import itertools
import logging
from string import Formatter
from zoneinfo import ZoneInfo

import dateutil
import numpy as np

from earthkit.plots import metadata
from earthkit.plots.schemas import schema
from earthkit.plots.utils import string_utils

logger = logging.getLogger(__name__)


def parse_time(time):
    return [dateutil.parser.parse(str(t)) for t in time]


SPECIAL_METHODS = {
    "parse_time": parse_time,
}


class BaseFormatter(Formatter):
    """
    Formatter of earthkit-plots components, enabling convient titles and labels.
    """

    #: Attributes of subplots which can be extracted by format strings
    SUBPLOT_ATTRIBUTES = {
        "domain": "domain_name",
        "crs": "crs_name",
    }

    #: Attributes of styles which can be extracted by format strings
    STYLE_ATTRIBUTES = {
        "units": "units",
    }

    def convert_field(self, value, conversion):
        """
        Convert a field value according to the conversion type.

        Parameters
        ----------
        value : object
            The value to be converted.
        conversion : str
            The conversion type.
        """
        if conversion == "u":
            return str(value).upper()
        elif conversion == "l":
            return str(value).lower()
        elif conversion == "c":
            return str(value).capitalize()
        elif conversion == "t":
            return str(value).title()
        return super().convert_field(value, conversion)

    def format_keys(self, format_string, kwargs):
        """
        Format keys in a format string.

        Parameters
        ----------
        format_string : str
            The format string.
        kwargs : dict
            The keyword arguments to be formatted.
        """
        keys = (i[1] for i in self.parse(format_string) if i[1] is not None)
        for key in keys:
            main_key, *methods = key.split(".")
            result = self.format_key(main_key)
            for method in methods:
                if method in SPECIAL_METHODS:
                    result = SPECIAL_METHODS[method](result)
                else:
                    result = getattr(np, method)(result)
                if not isinstance(result, (list, tuple, np.ndarray)):
                    result = [result]
            kwargs[key] = result
        return kwargs

    def format_key(self, key):
        return key

    def format(self, format_string, /, *args, **kwargs):
        kwargs = self.format_keys(format_string, kwargs)
        keys = list(kwargs)
        for key in keys:
            if "." in key:
                replacement_key = key.replace(".", "_")
                kwargs[replacement_key] = kwargs.pop(key)
                format_string = format_string.replace(key, replacement_key)
        return super().format(format_string, *args, **kwargs)


class SourceFormatter(BaseFormatter):
    """
    Formatter of earthkit-plots `Layers`, enabling convient titles and labels.
    """

    def __init__(self, source):
        self.source = source

    def format_key(self, key):
        return [metadata.labels.extract(self.source, key)[0]]


class LayerFormatter(BaseFormatter):
    """
    Formatter of earthkit-plots `Layers`, enabling convient titles and labels.
    """

    def __init__(self, layer):
        self.layer = layer

    def format_key(self, key):
        if key in self.SUBPLOT_ATTRIBUTES:
            value = getattr(self.layer.subplot, self.SUBPLOT_ATTRIBUTES[key])
        elif key in self.STYLE_ATTRIBUTES and self.layer.style is not None:
            value = getattr(self.layer.style, self.STYLE_ATTRIBUTES[key])
            if value is None:
                value = metadata.labels.extract(self.layer.source, key)
                if key == "units":
                    value = metadata.units.format_units(value)
        else:
            value = metadata.labels.extract(self.layer.source, key)
        return value


class SubplotFormatter(BaseFormatter):
    """
    Formatter of earthkit-plots `Subplots`, enabling convient titles and labels.
    """

    def __init__(self, subplot, unique=True):
        self.subplot = subplot
        self.unique = unique
        self._layer_index = None

    def convert_field(self, value, conversion):
        f = super().convert_field
        if isinstance(value, list):
            if isinstance(conversion, str) and conversion.isnumeric():
                return str(value[int(conversion)])
            return [f(v, conversion) for v in value]
        else:
            return f(value, conversion)

    def format_key(self, key):
        if key in self.SUBPLOT_ATTRIBUTES:
            values = [getattr(self.subplot, self.SUBPLOT_ATTRIBUTES[key])]
        else:
            values = [
                LayerFormatter(layer).format_key(key) for layer in self.subplot.layers
            ]
        return values

    def format_field(self, value, format_spec):
        f = super().format_field
        if isinstance(value, list):
            values = [f(v, format_spec) for v in value]
            if self._layer_index is not None:
                value = values[self._layer_index]
                self._layer_index = None
            else:
                if self.unique:
                    values = list(dict.fromkeys(values))
                value = string_utils.list_to_human(values)
        return value


class FigureFormatter(BaseFormatter):
    """
    Formatter of earthkit-plots `Charts`, enabling convient titles and labels.
    """

    def __init__(self, subplots, unique=True):
        self.subplots = subplots
        self.unique = unique
        self._layer_index = None

    def convert_field(self, value, conversion):
        f = super().convert_field
        if isinstance(value, list):
            if isinstance(conversion, str) and conversion.isnumeric():
                return str(value[int(conversion)])
            return [f(v, conversion) for v in value]
        else:
            return f(value, conversion)

    def format_key(self, key):
        values = [
            SubplotFormatter(subplot).format_key(key) for subplot in self.subplots
        ]
        values = [item for sublist in values for item in sublist]
        return values

    def format_field(self, value, format_spec):
        f = super().format_field
        if isinstance(value, list):
            values = [f(v, format_spec) for v in value]
            if self._layer_index is not None:
                value = values[self._layer_index]
                self._layer_index = None
            else:
                if self.unique:
                    values = list(dict.fromkeys(values))
                value = string_utils.list_to_human(values)
        return value


class TimeFormatter:
    """
    Formatter of time data, enabling convient time labels.

    Parameters
    ----------
    times : list
        The times to be formatted.
    time_zone : str, optional
        The time zone to be used for the times.
    """

    def __init__(self, times, time_zone=None):
        if not isinstance(times, (list, tuple)):
            times = [times]
        for i, time in enumerate(times):
            if not isinstance(time, dict):
                times[i] = {"time": time}
        self.times = times
        time_zone = time_zone or schema.time_zone
        self._time_zone = time_zone if time_zone is None else ZoneInfo(time_zone)

    def _extract_time(method):
        def wrapper(self):
            attr = method.__name__
            times = [self._named_time(time, attr) for time in self.times]
            if len(np.array(times).shape) > 1 and np.array(times).shape[0] == 1:
                times = times[0]
            _, indices = np.unique(times, return_index=True)
            result = [times[i] for i in sorted(indices)]
            if self._time_zone is not None:
                if None in [t.tzinfo for t in result]:
                    logger.warning(
                        "Attempting time zone conversion, but some data has no "
                        "time zone metadata; assuming UTC"
                    )
                    result = [
                        t if t.tzinfo is not None else t.replace(tzinfo=ZoneInfo("UTC"))
                        for t in result
                    ]
                result = [t.astimezone(tz=self._time_zone) for t in result]
            return result

        return property(wrapper)

    @staticmethod
    def _named_time(time, attr):
        return time.get(attr, time.get("time"))

    @property
    def time(self):
        """The most basic representation of time."""
        return self.valid_time

    @property
    def utc_offset(self):
        """The offset in hours from UTC."""
        valid_times = self.valid_time
        if None in [vt.tzinfo for vt in valid_times]:
            logger.warning(
                "Some of the data is missing time zone metadata; assuming UTC"
            )
            valid_times = [
                t if t.tzinfo is not None else t.replace(tzinfo=ZoneInfo("UTC"))
                for t in valid_times
            ]
        offsets = [vt.utcoffset().seconds // 3600 for vt in valid_times]
        time_zones = [f"UTC{offset:+d}" for offset in offsets]
        return time_zones

    @_extract_time
    def base_time(self):
        """The base time of the data, i.e. the time of the forecast."""
        pass

    @_extract_time
    def valid_time(self):
        """The valid time of the data, i.e. the time the forecast is for."""
        pass

    @property
    def lead_time(self):
        """The lead time of the data, i.e. the time between the base and valid times."""
        if len(self.base_time) == 1 and len(self.valid_time) > 1:
            times = itertools.product(self.base_time, self.valid_time)
        elif len(self.base_time) == len(self.valid_time):
            times = zip(self.base_time, self.valid_time)
        else:
            times = [
                (
                    self._named_time(time, "base_time"),
                    self._named_time(time, "valid_time"),
                )
                for time in self.times
            ]
        return [int((vtime - btime).total_seconds() / 3600) for btime, vtime in times]


def format_month(data):
    """
    Extract the month of the data time.

    Parameters
    ----------
    data : earthkit.maps.sources.Source
        The data source.
    """
    import calendar

    month = data.metadata("month", default=None)
    if month is not None:
        month = calendar.month_name[month]
    else:
        time = data.datetime()
        if "valid_time" in time:
            time = time["valid_time"]
        else:
            time = time["base_time"]
        month = f"{time:%B}"
    return month
