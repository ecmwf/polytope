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
import numpy as np
from matplotlib.colors import BoundaryNorm, LinearSegmentedColormap, ListedColormap


def expand(colors, levels, extend_colors=0):
    """
    Generate a list of colours from a matplotlib colormap name and some levels.

    Parameters
    ----------
    colors : str or list
        The name of a matplotlib colormap or a list of colours.
    levels : list
        The levels for which to generate colours.
    extend_colors : int, optional
        The number of colours to add to the colormap. Useful for extending the
        colormap to include under and over colours.
    """
    length = len(levels) + extend_colors

    if isinstance(colors, (list, tuple)) and len(colors) == 1:
        colors *= length - 1
    if isinstance(colors, str):
        try:
            cmap = mpl.colormaps[colors]
        except KeyError:
            colors = [colors] * (length - 1)
        else:
            colors = [cmap(i) for i in np.linspace(0, 1, length)]
    return colors


def contour_line_colors(colors, levels):
    """
    Generate a list of colours from a matplotlib colormap name and some levels.

    Parameters
    ----------
    colors : str or list
        The name of a matplotlib colormap or a list of colours.
    levels : list
        The levels for which to generate colours.
    """
    colors = expand(colors, levels)
    cmap = LinearSegmentedColormap.from_list(name="", colors=colors, N=len(levels))
    return cmap


def cmap_and_norm(colors, levels, normalize=True, extend=None, extend_levels=True):
    """
    Generate a colormap and a norm from a list of colours and levels.

    Parameters
    ----------
    colors : str or list
        The name of a matplotlib colormap or a list of colours.
    levels : list
        The levels for which to generate colours.
    normalize : bool, optional
        Whether to normalize the colors.
    extend : str, optional
        Whether to extend the colormap. Options are "both", "min", "max" or None.
    extend_levels : bool, optional
        Whether to extend the levels. If False, the levels will be used as is.
        If True, the levels will be extended to include the under and over values.
    """
    levels = list(levels)
    extend_colors = 0
    color_levels = levels
    if extend == "both":
        if extend_levels:
            levels = [-np.inf] + levels + [np.inf]
        extend_colors = 2
        color_levels = [min(levels) - 1] + levels + [max(levels) + 1]
    elif extend == "max":
        if extend_levels:
            levels += [np.inf]
        extend_colors = 1
        color_levels = levels + [max(levels) + 1]
    elif extend == "min":
        if extend_levels:
            levels = [-np.inf] + levels
        extend_colors = 1
        color_levels = [min(levels) - 1] + levels

    if extend_levels:
        color_levels = levels

    colors = expand(colors, color_levels, extend_colors)
    N = len(color_levels) + extend_colors - 1

    colormap = LinearSegmentedColormap.from_list
    if len(colors) == N:
        colormap = ListedColormap

    if extend_levels:
        cmap = colormap(name="", colors=colors, N=N)
    else:
        cmap_colors = colors
        if extend == "both":
            cmap_colors = colors[1:-1]
        elif extend == "min":
            cmap_colors = colors[1:]
        elif extend == "max":
            cmap_colors = colors[:-1]
        cmap = colormap(name="", colors=cmap_colors, N=len(cmap_colors) - 1)
        cmap.set_over(colors[-1])
        cmap.set_under(colors[0])

    norm = None
    if normalize:
        norm = BoundaryNorm(levels, cmap.N)

    return cmap, norm


def gradients(levels, colors, gradients, normalize, **kwargs):
    """
    Generate a colormap with a specified number of gradients between levels.

    Parameters
    ----------
    levels : list
        The levels for which to generate colours.
    colors : list
        The colours to use for the levels.
    gradients : int or list
        The number of gradients between each level.
    normalize : bool
        Whether to normalize the colours.
    **kwargs
        Additional keyword arguments to pass to the colormap.
    """
    normalised = (levels - np.min(levels)) / (np.max(levels) - np.min(levels))
    color_bins = list(zip(normalised, colors))
    cmap = LinearSegmentedColormap.from_list(name="", colors=color_bins, N=255)

    if not isinstance(gradients, (list, tuple)):
        gradients = [gradients] * (len(levels) - 1)

    extrapolated_levels = []
    for i in range(len(levels) - 1):
        bins = list(np.linspace(levels[i], levels[i + 1], gradients[i]))
        extrapolated_levels += bins[(1 if i != 0 else 0) :]
    levels = extrapolated_levels

    norm = None
    if normalize:
        norm = BoundaryNorm(levels, cmap.N)

    return {**{"cmap": cmap, "norm": norm, "levels": levels}, **kwargs}
