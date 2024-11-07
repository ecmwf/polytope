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

from pathlib import Path

import matplotlib.pyplot as plt
import yaml
from matplotlib import rcParams

from earthkit.plots._plugins import PLUGINS
from earthkit.plots.geo.coordinate_reference_systems import parse_crs
from earthkit.plots.utils.dict_utils import recursive_dict_update

_DEFAULT_SCHEMA = "default"


RCPARAMS = [
    "backends",
    "lines",
    "patches",
    "hatches",
    "font",
    "text",
    "latex",
    "axes",
    "dates",
    "xtick",
    "ytick",
    "grid",
    "figure",
    "images",
    "errorbar",
    "histogram",
    "agg",
    "paths",
    "saving",
    "interactive keymaps",
    "animation",
]


class SchemaNotFoundError(FileNotFoundError):
    pass


class _set:
    def __init__(self, schema, **kwargs):
        self.schema = schema

        keys = [key for key in kwargs if key in self.schema]

        self.old_kwargs = {key: self.schema.get(key) for key in keys}
        self.old_kwargs = {
            **self.old_kwargs,
            **{
                key: dict(value)
                for key, value in self.old_kwargs.items()
                if isinstance(value, Schema)
            },
        }

        self.new_kwargs = [key for key in kwargs if key not in self.schema]
        self.schema._update(**kwargs)

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.schema._update(**self.old_kwargs)
        for key in self.new_kwargs:
            self.schema.pop(key, None)


class Schema(dict):
    """Class for containing and maintaining global style settings."""

    PROTECTED_KEYS = ["_parent"]

    parsers = {
        "reference_crs": parse_crs,
    }

    def __init__(self, parent=None, **kwargs):
        self._parent = parent
        self._update(**kwargs)
        self._apply_rcParams()

    def _apply_rcParams(self):
        if "style_sheet" in self:
            plt.style.use(self["style_sheet"])
        for param, config in self.items():
            if param in RCPARAMS and self._parent is None:
                for member, value in config.items():
                    if member in Schema.PROTECTED_KEYS:
                        continue
                    rcParams[".".join((param, member))] = value

    def __getattr__(self, key):
        if key in self:
            return self[key]
        raise AttributeError(key)

    def __setattr__(self, key, value):
        if isinstance(value, dict) and not isinstance(value, Schema):
            value = Schema(parent=key, **value)
        try:
            self[key] = value
        except KeyError:
            raise AttributeError(key)
        if self._parent in RCPARAMS and key not in Schema.PROTECTED_KEYS:
            rcParams[".".join((self._parent, key))] = value

    def __repr__(self):
        return f"{self.__class__.__name__}({super().__repr__()})"

    def _update(self, **kwargs):
        for key, value in kwargs.items():
            if key in self.parsers:
                value = self.parsers[key](value)
            setattr(self, key, value)

    def apply(self, *keys):
        def decorator(function):
            def wrapper(*args, **kwargs):
                return function(*args, **self._update_kwargs(kwargs, keys))

            return wrapper

        return decorator

    def _update_kwargs(self, kwargs, keys):
        schema_kwargs = self._to_dict()
        if keys:
            schema_kwargs = {
                key: schema_kwargs[key]
                for key in keys
                if key not in Schema.PROTECTED_KEYS
            }
        return recursive_dict_update(schema_kwargs, kwargs)

    def _to_dict(self):
        d = dict()
        for key in self:
            if key in Schema.PROTECTED_KEYS:
                continue
            value = getattr(self, key)
            if isinstance(value, type(self)):
                value = value._to_dict()
            d[key] = value
        return d

    def set(self, **kwargs):
        """
        Set the value of a schema key.

        Parameters
        ----------
        **kwargs
            The schema keys and values to set.

        Example
        -------
        >>> schema.set(font="verdana")
        >>> with schema.set(font="comic sans"):
        ...     print(schema.font)
        ...
        comic sans
        >>> print(schema.font)
        verdana
        """
        return _set(self, **kwargs)

    def get(self, key):
        """
        Get the value of a schema key.

        Parameters
        ----------
        key : str
            The name of the schema key to get.

        Example
        -------
        >>> schema.set(font="verdana")
        >>> schema.get("font")
        'verdana'
        """
        return getattr(self, key)

    def use(self, name):
        """
        Use a named schema.

        Parameters
        ----------
        name : str
            The name of the schema to use, or path to a user-implemented schema.

        Example
        -------
        >>> schema.use("default")
        >>> schema.use("~/custom.yaml")
        """
        if name not in PLUGINS:
            file_name = Path(name).expanduser()
            if not file_name.exists():
                raise SchemaNotFoundError(f"No plugin '{name}' found")
        elif PLUGINS[name].get("schema") is None:
            raise SchemaNotFoundError(f"No schema found in '{name}' plugin")
        else:
            file_name = PLUGINS[name]["schema"]

        with open(file_name, "r") as f:
            kwargs = yaml.load(f, Loader=yaml.SafeLoader)

        self._reset(**kwargs)

    def _reset(self, **kwargs):
        self.__init__(**kwargs)


schema = Schema()
schema.use(_DEFAULT_SCHEMA)
