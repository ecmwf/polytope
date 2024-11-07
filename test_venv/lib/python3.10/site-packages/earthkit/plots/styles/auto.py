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

import glob
import os
from pathlib import Path

import yaml

from earthkit.plots import styles
from earthkit.plots._plugins import PLUGINS
from earthkit.plots.metadata.units import are_equal
from earthkit.plots.schemas import schema


def guess_style(data, units=None, **kwargs):
    """
    Guess the style to be applied to the data based on its metadata.

    The style is guessed by comparing the metadata of the data to the identities
    and styles in the style library. The first identity that matches the metadata
    is used to select the style. If the style library is not set or no identity
    matches the metadata, the default style is returned.

    Parameters
    ----------
    data : earthkit.plots.sources.Source
        The data object containing the metadata.
    units : str, optional
        The target units of the plot. If these do not match the units of the
        data, the data will be converted to the target units and the style
        will be adjusted accordingly.
    """
    if not schema.automatic_styles or schema.style_library is None:
        return styles.DEFAULT_STYLE

    if schema.style_library not in PLUGINS:
        path = Path(schema.style_library).expanduser()
        identities_path = path / "identities"
        styles_path = path / "styles"
    else:
        identities_path = PLUGINS[schema.style_library]["identities"]
        styles_path = PLUGINS[schema.style_library]["styles"]

    identity = None

    for fname in glob.glob(str(identities_path / "*")):
        if os.path.isfile(fname):
            with open(fname, "r") as f:
                config = yaml.load(f, Loader=yaml.SafeLoader)
        else:
            continue

        for criteria in config["criteria"]:
            for key, value in criteria.items():
                if data.metadata(key, default=None) == value:
                    identity = config["id"]
                    break
            else:
                continue
            break
        else:
            continue
        break
    else:
        return styles.DEFAULT_STYLE

    for fname in glob.glob(str(styles_path / "*")):
        if os.path.isfile(fname):
            with open(fname, "r") as f:
                style_config = yaml.load(f, Loader=yaml.SafeLoader)
        else:
            continue
        if style_config["id"] == identity:
            break
    else:
        return styles.DEFAULT_STYLE

    if schema.use_preferred_units:
        style = style_config["styles"][style_config["optimal"]]
    else:
        for _, style in style_config["styles"].items():
            if are_equal(style.get("units"), units):
                break
        else:
            # No style matching units found; return default
            return styles.DEFAULT_STYLE

    return styles.Style.from_dict({**style, **kwargs})
