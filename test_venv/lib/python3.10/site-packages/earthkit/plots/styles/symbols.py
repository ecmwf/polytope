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


import matplotlib as mpl
from svgpath2mpl import parse_path
from svgpathtools import svg2paths

from earthkit.plots.definitions import SYMBOLS_DIR


def get_symbol(name):
    """
    Get a symbol from an SVG file.

    Parameters
    ----------
    name : str
        The name of the symbol.
    """
    _, attributes = svg2paths(SYMBOLS_DIR / f"{name}.svg")
    marker = parse_path(attributes[0]["d"])
    marker.vertices -= marker.vertices.mean(axis=0)
    marker = marker.transformed(mpl.transforms.Affine2D().rotate_deg(180))
    marker = marker.transformed(mpl.transforms.Affine2D().scale(-1, 1))
    return marker


HURRICANE = get_symbol("hurricane")
