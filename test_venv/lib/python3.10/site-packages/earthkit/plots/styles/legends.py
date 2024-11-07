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


DEFAULT_LEGEND_LABEL = "{variable_name} ({units})"

_DISJOINT_LEGEND_LOCATIONS = {
    "bottom": {
        "loc": "upper center",
        "bbox_to_anchor": (0.5, -0.05),
    },
    "top": {
        "loc": "lower center",
        "bbox_to_anchor": (0.5, 1.0),
    },
    "left": {
        "loc": "upper right",
        "bbox_to_anchor": (-0.05, 1.0),
    },
    "right": {
        "loc": "upper left",
        "bbox_to_anchor": (1.05, 1.0),
    },
    "top left": {
        "loc": "lower center",
        "bbox_to_anchor": (0.25, 1),
    },
    "top right": {
        "loc": "lower center",
        "bbox_to_anchor": (0.75, 1),
    },
}


def colorbar(layer, *args, shrink=0.8, aspect=35, ax=None, **kwargs):
    """
    Produce a colorbar for a given layer.

    Parameters
    ----------
    layer : earthkit.maps.charts.layers.Layer
        The layer for which to produce a colorbar.
    **kwargs
        Any keyword arguments accepted by `matplotlib.figures.Figure.colorbar`.
    """
    label = kwargs.pop("label", DEFAULT_LEGEND_LABEL)
    try:
        label = layer.format_string(label)
    except (AttributeError, ValueError, KeyError):
        label = ""

    kwargs = {**layer.style._legend_kwargs, **kwargs}
    kwargs.setdefault("format", lambda x, _: f"{x:g}")

    if ax is None:
        kwargs["ax"] = layer.axes
    else:
        kwargs["cax"] = ax

    cbar = layer.fig.colorbar(
        layer.mappable,
        *args,
        label=label,
        shrink=shrink,
        aspect=aspect,
        **kwargs,
    )
    cbar.ax.minorticks_off()
    cbar.ax.tick_params(size=0)

    if cbar.solids is not None:
        cbar.solids.set(alpha=1)

    return cbar


def disjoint(layer, *args, location="bottom", frameon=False, **kwargs):
    """
    Produce a disjoint legend for a given layer.

    Parameters
    ----------
    layer : earthkit.maps.charts.layers.Layer
        The layer for which to produce a colorbar.
    **kwargs
        Any keyword arguments accepted by `matplotlib.figures.Figure.legend`.
    """
    kwargs.pop("format")  # remove higher-level kwargs which are invalid

    label = kwargs.pop("label", DEFAULT_LEGEND_LABEL)
    label = layer.format_string(label)

    source = layer.axes[0] if len(layer.axes) == 1 else layer.fig
    location_kwargs = _DISJOINT_LEGEND_LOCATIONS[location]

    artists, labels = layer.mappable.legend_elements()

    kwargs["ncols"] = kwargs.get("ncols", min(6, len(artists)))

    labels = kwargs.pop("labels", layer.style._bin_labels) or labels
    legend = source.legend(
        artists,
        labels,
        *args,
        title=label,
        frameon=frameon,
        **{**location_kwargs, **kwargs},
    )

    # Matplotlib removes legends when a new legend is plotted, so we have
    # to manually re-add them...
    if hasattr(layer.fig, "_previous_legend"):
        layer.fig.add_artist(layer.fig._previous_legend)
    layer.fig._previous_legend = legend

    layer.fig.canvas.draw()

    return legend
