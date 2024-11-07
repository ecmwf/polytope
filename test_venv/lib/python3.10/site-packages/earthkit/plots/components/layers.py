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


from earthkit.plots import metadata
from earthkit.plots.metadata.formatters import LayerFormatter
from earthkit.plots.utils import string_utils


class Layer:
    """
    A single plot Layer on a Subplot.

    Parameters
    ----------
    source : earthkit.maps.sources.Source
        The source of the data to be plotted.
    mappable : matplotlib object
        The object that is plotted on the axes.
    subplot : earthkit.plots.components.subplots.Subplot
        The subplot on which this layer is plotted.
    style : earthkit.plots.styles.Style, optional
        The style to be applied to this layer.
    """

    def __init__(self, source, mappable, subplot, style=None):
        self.source = source
        self.mappable = mappable
        self.subplot = subplot
        self.style = style

    @property
    def fig(self):
        """The matplotlib figure on which this layer is plotted."""
        return self.subplot.fig

    @property
    def ax(self):
        """The matplotlib axes on which this layer is plotted."""
        return self.subplot.ax

    @property
    def axes(self):
        """All matplotlib axes over which this layer is plotted."""
        return [self.ax]

    def legend(self, *args, **kwargs):
        """
        Generate a legend for this specific layer.
        """
        if self.style is not None:
            return self.style.legend(self, *args, **kwargs)

    def format_string(self, string):
        return LayerFormatter(self).format(string)

    @property
    def _default_title_template(self):
        if self.source.metadata("type", default="an") == "an":
            template = metadata.labels.DEFAULT_ANALYSIS_TITLE
        else:
            template = metadata.labels.DEFAULT_FORECAST_TITLE
        return template


class LayerGroup:
    """
    A group of related layers.

    Parameters
    ----------
    layers : list of earthkit.maps.charts.layers.Layer objects
        A list of grouped layers.
    """

    def __init__(self, layers):
        self.layers = layers

    @property
    def subplots(self):
        """The subplots on which this layer group is plotted."""
        return [layer.subplot for layer in self.layers]

    @property
    def fig(self):
        """The matplotlib figure on which this layer group is plotted."""
        return self.subplots[0].fig

    @property
    def axes(self):
        """All matplotlib axes over which this layer group is plotted."""
        return [subplot.ax for subplot in self.subplots]

    @property
    def style(self):
        """The style to be applied to this layer group."""
        return self.layers[0].style

    def legend(self, *args, **kwargs):
        """
        Add a legend for this layer group.

        Parameters
        ----------
        *args : list
            Arguments to be passed to the style.legend method.
        **kwargs : dict
            Keyword arguments to be passed to the style.legend method.
        """
        if self.style is not None:
            return self.style.legend(
                self.fig,
                self,
                *args,
                ax=self.axes,
                **kwargs,
            )

    @property
    def mappable(self):
        """The object that is plotted on the axes."""
        return self.layers[0].mappable

    def format_string(self, string, unique=True):
        """
        Format a string with the layer group's metadata.

        Parameters
        ----------
        string : str
            The string to be formatted. Can contain placeholders for the layer
            group's metadata in the form of `{key}`.
        unique : bool, optional
            Whether to return only unique values for each placeholder. If False,
            all values will be returned.
        """
        results = [layer.format_string(string) for layer in self.layers]

        if unique:
            results = list(dict.fromkeys(results))

        result = string_utils.list_to_human(results)
        return result
