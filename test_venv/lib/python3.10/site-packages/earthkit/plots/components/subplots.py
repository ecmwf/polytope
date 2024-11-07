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

import warnings
from itertools import cycle

import earthkit.data
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import numpy as np

from earthkit.plots import identifiers
from earthkit.plots.components.layers import Layer
from earthkit.plots.geo import grids
from earthkit.plots.metadata.formatters import (
    LayerFormatter,
    SourceFormatter,
    SubplotFormatter,
)
from earthkit.plots.schemas import schema
from earthkit.plots.sources import get_source, single
from earthkit.plots.styles import _OVERRIDE_KWARGS, _STYLE_KWARGS, Contour, Style, auto
from earthkit.plots.utils import iter_utils, string_utils

DEFAULT_FORMATS = ["%Y", "%b", "%-d", "%H:%M", "%H:%M", "%S.%f"]
ZERO_FORMATS = ["%Y", "%b", "%-d", "%H:%M", "%H:%M", "%S.%f"]


class Subplot:
    """
    A single plot within a Figure.

    A Subplot is a container for one or more Layers, each of which is a plot of
    a single data source.

    Parameters
    ----------
    row : int, optional
        The row index of the subplot in the Figure.
    column : int, optional
        The column index of the subplot in the Figure.
    figure : Figure, optional
        The Figure to which the subplot belongs.
    **kwargs
        Additional keyword arguments to pass to the matplotlib Axes constructor.
    """

    def __init__(self, row=0, column=0, figure=None, **kwargs):
        self._figure = figure
        self._ax = None
        self._ax_kwargs = kwargs

        self.layers = []

        self.row = row
        self.column = column

        self.domain = None

    def set_major_xticks(
        self,
        frequency=None,
        format=None,
        highlight=None,
        highlight_color="red",
        **kwargs,
    ):
        formats = DEFAULT_FORMATS
        if frequency is None:
            locator = mdates.AutoDateLocator(maxticks=30)
        else:
            if frequency.startswith("D"):
                interval = frequency.lstrip("D") or 1
                if interval is not None:
                    interval = int(interval)
                locator = mdates.DayLocator(interval=interval, **kwargs)
            elif frequency.startswith("M"):
                interval = int(frequency.lstrip("M") or "1")
                locator = mdates.MonthLocator(interval=interval, bymonthday=15)
            elif frequency.startswith("Y"):
                locator = mdates.YearLocator()
            elif frequency.startswith("H"):
                interval = int(frequency.lstrip("H") or "1")
                locator = mdates.HourLocator(interval=interval)

        if format:
            formats = [format] * 6

        formatter = mdates.ConciseDateFormatter(
            locator, formats=formats, zero_formats=ZERO_FORMATS, show_offset=False
        )
        self.ax.xaxis.set_major_locator(locator)
        self.ax.xaxis.set_major_formatter(formatter)

        if highlight is not None:
            dates = [mdates.num2date(i) for i in self.ax.get_xticks()]
            for i, date in enumerate(dates):
                highlight_this = False
                for key, value in highlight.items():
                    attr = getattr(date, key)
                    attr = attr if not callable(attr) else attr()
                    if isinstance(value, list):
                        if attr in value:
                            highlight_this = True
                    else:
                        if attr == value:
                            highlight_this = True
                if highlight_this:
                    self.ax.get_xticklabels()[i].set_color(highlight_color)

    def set_minor_xticks(
        self,
        frequency=None,
        format=None,
        **kwargs,
    ):
        formats = DEFAULT_FORMATS
        if frequency is None:
            locator = mdates.AutoDateLocator(maxticks=30)
        else:
            if frequency.startswith("D"):
                interval = frequency.lstrip("D") or 1
                if interval is not None:
                    interval = int(interval)
                locator = mdates.DayLocator(interval=interval, **kwargs)
            elif frequency.startswith("M"):
                interval = int(frequency.lstrip("M") or "1")
                locator = mdates.MonthLocator(interval=interval, bymonthday=15)
            elif frequency.startswith("Y"):
                locator = mdates.YearLocator()
            elif frequency.startswith("H"):
                interval = int(frequency.lstrip("H") or "1")
                locator = mdates.HourLocator(interval=interval)

        if format:
            formats = [format] * 6

        formatter = mdates.ConciseDateFormatter(
            locator, formats=formats, zero_formats=ZERO_FORMATS, show_offset=False
        )
        self.ax.xaxis.set_minor_locator(locator)
        self.ax.xaxis.set_minor_formatter(formatter)

    def plot_2D(method_name=None):
        def decorator(method):
            def wrapper(
                self,
                data=None,
                x=None,
                y=None,
                z=None,
                style=None,
                **kwargs,
            ):
                return self._extract_plottables(
                    method_name or method.__name__,
                    args=tuple(),
                    data=data,
                    x=x,
                    y=y,
                    z=z,
                    style=style,
                    **kwargs,
                )

            return wrapper

        return decorator

    def plot_box(method_name=None):
        def decorator(method):
            def wrapper(self, data=None, x=None, y=None, z=None, style=None, **kwargs):
                source = get_source(data=data, x=x, y=y, z=z)
                kwargs = {**self._plot_kwargs(source), **kwargs}
                m = getattr(self.ax, method_name or method.__name__)
                if source.extract_x() in identifiers.TIME:
                    positions = mdates.date2num(source.x_values)
                else:
                    positions = source.x_values
                widths = min(0.5, np.diff(positions).min() * 0.7)
                mappable = m(
                    source.z_values, positions=positions, widths=widths, **kwargs
                )
                self.layers.append(Layer(source, mappable, self, style))
                if isinstance(source._x, str):
                    if source._x in identifiers.TIME:
                        locator = mdates.AutoDateLocator(maxticks=30)
                        formatter = mdates.ConciseDateFormatter(
                            locator,
                            formats=["%Y", "%b", "%-d %b", "%H:%M", "%H:%M", "%S.%f"],
                        )
                        self.ax.xaxis.set_major_locator(locator)
                        self.ax.xaxis.set_major_formatter(formatter)
                    else:
                        self.ax.set_xlabel(source._x)
                if isinstance(source._z, str):
                    self.ax.set_ylabel(source._z)
                return mappable

            return wrapper

        return decorator

    def plot_3D(method_name=None, extract_domain=False):
        def decorator(method):
            def wrapper(
                self,
                data=None,
                x=None,
                y=None,
                z=None,
                style=None,
                every=None,
                **kwargs,
            ):
                return self._extract_plottables(
                    method_name or method.__name__,
                    args=tuple(),
                    data=data,
                    x=x,
                    y=y,
                    z=z,
                    style=style,
                    every=every,
                    extract_domain=extract_domain,
                    **kwargs,
                )

            return wrapper

        return decorator

    def plot_vector(method_name=None):
        def decorator(method):
            def wrapper(
                self,
                data=None,
                x=None,
                y=None,
                z=None,
                u=None,
                v=None,
                colors=False,
                every=None,
                **kwargs,
            ):
                source = get_source(data=data, x=x, y=y, z=z, u=u, v=v)
                kwargs = {**self._plot_kwargs(source), **kwargs}
                m = getattr(self.ax, method_name or method.__name__)

                x_values = source.x_values
                y_values = source.y_values
                u_values = source.u_values
                v_values = source.v_values

                if self.domain is not None:
                    x_values, y_values, _, [u_values, v_values] = self.domain.extract(
                        x_values,
                        y_values,
                        extra_values=[u_values, v_values],
                        source_crs=source.crs,
                    )

                if every is None:
                    args = [x_values, y_values, u_values, v_values]
                else:
                    args = [
                        thin_array(x_values, every=every),
                        thin_array(y_values, every=every),
                        thin_array(u_values, every=every),
                        thin_array(v_values, every=every),
                    ]
                if colors:
                    if every is None:
                        args.append(source.magnitude_values)
                    else:
                        args.append(source.magnitude_values[::every, ::every])

                mappable = m(*args, **kwargs)
                self.layers.append(Layer(source, mappable, self))
                if isinstance(source._x, str):
                    self.ax.set_xlabel(source._x)
                if isinstance(source._y, str):
                    self.ax.set_ylabel(source._y)
                return mappable

            return wrapper

        return decorator

    def _extract_plottables(
        self,
        method_name,
        args,
        data=None,
        x=None,
        y=None,
        z=None,
        style=None,
        units=None,
        every=None,
        source_units=None,
        extract_domain=False,
        **kwargs,
    ):
        if source_units is not None:
            source = get_source(*args, data=data, x=x, y=y, z=z, units=source_units)
        else:
            source = get_source(*args, data=data, x=x, y=y, z=z)
        kwargs = {**self._plot_kwargs(source), **kwargs}
        if method_name == "contourf":
            source.regrid = True
        if style is None:
            style_kwargs = {
                key: kwargs.pop(key) for key in _STYLE_KWARGS if key in kwargs
            }
            # These are kwargs which can be overridden without forcing a new Style
            override_kwargs = {
                key: style_kwargs.pop(key)
                for key in _OVERRIDE_KWARGS
                if key in style_kwargs
            }
            if style_kwargs:
                style_class = (
                    Style if not method_name.startswith("contour") else Contour
                )
                style = style_class(**{**style_kwargs, **{"units": units}})
            else:
                style = auto.guess_style(
                    source, units=units or source.units, **override_kwargs
                )

        if data is None and z is None:
            z_values = None
        else:
            z_values = style.convert_units(source.z_values, source.units)
            z_values = style.apply_scale_factor(z_values)

        if (
            source.metadata("gridType", default=None) == "healpix"
            and method_name == "pcolormesh"
        ):
            from earthkit.plots.geo import healpix

            nest = source.metadata("orderingConvention", default=None) == "nested"
            kwargs["transform"] = self.crs
            mappable = healpix.nnshow(
                z_values, ax=self.ax, nest=nest, style=style, **kwargs
            )
        elif (
            source.metadata("gridType", default=None) == "reduced_gg"
            and method_name == "pcolormesh"
        ):
            from earthkit.plots.geo import reduced_gg

            x_values = source.x_values
            y_values = source.y_values
            kwargs["transform"] = self.crs
            mappable = reduced_gg.nnshow(
                z_values, x_values, y_values, ax=self.ax, style=style, **kwargs
            )
        else:
            x_values = source.x_values
            y_values = source.y_values

            if every is not None:
                x_values = x_values[::every]
                y_values = y_values[::every]
                if z_values is not None:
                    z_values = z_values[::every, ::every]

            if self.domain is not None and extract_domain:
                x_values, y_values, z_values = self.domain.extract(
                    x_values,
                    y_values,
                    z_values,
                    source_crs=source.crs,
                )
            if "interpolation_method" in kwargs:
                kwargs.pop("interpolation_method")
                warnings.warn(
                    "The 'interpolation_method' argument is only valid for unstructured data."
                )
            try:
                mappable = getattr(style, method_name)(
                    self.ax, x_values, y_values, z_values, **kwargs
                )
            except TypeError as err:
                if not grids.is_structured(x_values, y_values):
                    x_values, y_values, z_values = grids.interpolate_unstructured(
                        x_values,
                        y_values,
                        z_values,
                        method=kwargs.pop("interpolation_method", "linear"),
                    )
                    mappable = getattr(style, method_name)(
                        self.ax, x_values, y_values, z_values, **kwargs
                    )
                else:
                    raise err
        self.layers.append(Layer(source, mappable, self, style))
        return mappable

    def _extract_plottables_2(
        self,
        data=None,
        x=None,
        y=None,
        z=None,
        every=None,
        source_units=None,
        extract_domain=False,
        **kwargs,
    ):
        if source_units is not None:
            source = get_source(data=data, x=x, y=y, z=z, units=source_units)
        else:
            source = get_source(data=data, x=x, y=y, z=z)
        kwargs = {**self._plot_kwargs(source), **kwargs}

        if (data is None and z is None) or (z is not None and not z):
            z_values = None
        else:
            z_values = source.z_values

        x_values = source.x_values
        y_values = source.y_values

        if every is not None:
            x_values = x_values[::every]
            y_values = y_values[::every]
            if z_values is not None:
                z_values = z_values[::every, ::every]

        if self.domain is not None and extract_domain:
            x_values, y_values, z_values = self.domain.extract(
                x_values,
                y_values,
                z_values,
                source_crs=source.crs,
            )
        return x_values, y_values, z_values

    @property
    def figure(self):
        from earthkit.plots import Figure

        if self._figure is None:
            self._figure = Figure(1, 1)
            self._figure.subplots = [self]
        return self._figure

    @property
    def fig(self):
        """The underlying matplotlib Figure object."""
        return self.figure.fig

    @property
    def ax(self):
        """The underlying matplotlib Axes object."""
        if self._ax is None:
            self._ax = self.figure.fig.add_subplot(
                self.figure.gridspec[self.row, self.column], **self._ax_kwargs
            )
        return self._ax

    @property
    def _default_title_template(self):
        """The default title template for the Subplot."""
        templates = [layer._default_title_template for layer in self.layers]
        if len(set(templates)) == 1:
            template = templates[0]
        else:
            title_parts = []
            for i, template in enumerate(templates):
                keys = [k for _, k, _, _ in SubplotFormatter().parse(template)]
                for key in set(keys):
                    template = template.replace("{" + key, "{" + key + f"!{i}")
                title_parts.append(template)
            template = string_utils.list_to_human(title_parts)
        return template

    @property
    def distinct_legend_layers(self):
        """Layers on this subplot which have a unique `Style`."""
        unique_layers = []
        for layer in self.layers:
            for legend_layer in unique_layers:
                if legend_layer.style == layer.style:
                    break
            else:
                unique_layers.append(layer)
        return unique_layers

    def _plot_kwargs(self, *args, **kwargs):
        return dict()

    def coastlines(self, *args, **kwargs):
        raise NotImplementedError

    def gridlines(self, *args, **kwargs):
        raise NotImplementedError

    @plot_2D()
    def line(self, *args, **kwargs):
        """
        Plot a line on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x and y must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the line. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.plot`.
        """

    @schema.envelope.apply()
    def envelope(self, data_1, data_2=0, alpha=0.4, **kwargs):
        x1, y1, _ = self._extract_plottables_2(y=data_1, **kwargs)
        x2, y2, _ = self._extract_plottables_2(y=data_2, **kwargs)
        kwargs.pop("x")
        mappable = self.ax.fill_between(x=x1, y1=y1, y2=y2, alpha=alpha, **kwargs)
        self.layers.append(Layer(get_source(data=data_1), mappable, self, style=None))
        return mappable

    @schema.envelope.apply()
    def quantiles(self, data, quantiles=[0, 1], dim=None, alpha=0.15, **kwargs):
        prop_cycle = plt.rcParams["axes.prop_cycle"]
        facecolor = kwargs.pop(
            "facecolor", kwargs.get("color", next(cycle(prop_cycle.by_key()["color"])))
        )
        color = kwargs.pop("color", next(cycle(prop_cycle.by_key()["color"])))
        if isinstance(data, earthkit.data.core.Base):
            data = data.to_xarray()
        if dim is None:
            dim = list(data.dims)[0]
        for q in iter_utils.symmetrical_iter(quantiles):
            lines = data.quantile(q, dim=dim)
            if isinstance(q, tuple):
                x, y1, _ = self._extract_plottables_2(
                    y=lines.sel(quantile=q[0]), **kwargs
                )
                _, y2, _ = self._extract_plottables_2(
                    y=lines.sel(quantile=q[1]), **kwargs
                )
                mappable = self.ax.fill_between(
                    x=x,
                    y1=y1,
                    y2=y2,
                    facecolor=facecolor,
                    alpha=alpha,
                    **{k: v for k, v in kwargs.items() if k != "x"},
                )
            else:
                x, y, _ = self._extract_plottables_2(y=lines, **kwargs)
                kwargs.pop("label", None)
                mappable = self.ax.plot(
                    x, y, color=color, **{k: v for k, v in kwargs.items() if k != "x"}
                )

        # kwargs.pop("x")
        # mappable = self.ax.fill_between(x=x1, y1=y1, y2=y2, alpha=alpha, **kwargs)
        # self.layers.append(Layer(get_source(data=data_1), mappable, self, style=None))
        return mappable

    def labels(self, data=None, label=None, x=None, y=None, **kwargs):
        source = get_source(data=data, x=x, y=y)
        labels = SourceFormatter(source).format(label)
        for label, x, y in zip(labels, source.x_values, source.y_values):
            self.ax.annotate(label, (x, y), **kwargs)

    def plot(self, *args, style=None, **kwargs):
        if style is not None:
            method = getattr(self, style._preferred_method)
        else:
            method = self.block
        return method(*args, style=style, **kwargs)

    @plot_2D()
    def bar(self, *args, **kwargs):
        """
        Plot a bar chart on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x and y must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the bar chart. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.bar`.
        """

    @schema.scatter.apply()
    @plot_2D()
    def scatter(self, *args, **kwargs):
        """
        Plot a scatter plot on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x and y must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the scatter plot. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.scatter`.
        """

    # @schema.boxplot.apply()
    # @plot_box()
    # def boxplot(self, *args, **kwargs):
    #     """"""

    @plot_3D(extract_domain=True)
    def pcolormesh(self, *args, **kwargs):
        """
        Plot a pcolormesh on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, and z must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        z : str, list, numpy.ndarray, or xarray.DataArray, optional
            The z values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the pcolormesh. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.pcolormesh`.
        """

    @schema.contour.apply()
    @plot_3D(extract_domain=True)
    def contour(self, *args, **kwargs):
        """
        Plot a contour plot on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, and z must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        z : str, list, numpy.ndarray, or xarray.DataArray, optional
            The z values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the contour plot. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.contour`.
        """

    @plot_3D(extract_domain=True)
    def contourf(self, *args, **kwargs):
        """
        Plot a filled contour plot on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, and z must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        z : str, list, numpy.ndarray, or xarray.DataArray, optional
            The z values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the filled contour plot. If None, a Style is
            automatically generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.contourf`.
        """

    @plot_3D()
    def tripcolor(self, *args, **kwargs):
        """
        Plot a tripcolor plot on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, and z must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        z : str, list, numpy.ndarray, or xarray.DataArray, optional
            The z values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the tripcolor plot. If None, a Style is
            automatically generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.tripcolor`.
        """

    @plot_3D()
    def tricontour(self, *args, **kwargs):
        """
        Plot a tricontour plot on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, and z must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        z : str, list, numpy.ndarray, or xarray.DataArray, optional
            The z values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the tricontour plot. If None, a Style is
            automatically generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.tricontour`.
        """

    @plot_3D()
    def tricontourf(self, *args, **kwargs):
        """
        Plot a filled tricontour plot on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, and z must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        z : str, list, numpy.ndarray, or xarray.DataArray, optional
            The z values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the filled tricontour plot. If None, a Style is
            automatically generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.tricontourf`.
        """

    @schema.quiver.apply()
    @plot_vector()
    def quiver(self, *args, **kwargs):
        """
        Plot arrows on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, u, and v must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        u : str, list, numpy.ndarray, or xarray.DataArray, optional
            The u values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        v : str, list, numpy.ndarray, or xarray.DataArray, optional
            The v values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the quiver plot. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.quiver`.
        """

    @schema.barbs.apply()
    @plot_vector()
    def barbs(self, *args, **kwargs):
        """
        Plot wind barbs on the Subplot.

        Parameters
        ----------
        data : list, numpy.ndarray, xarray.DataArray, or earthkit.data.core.Base, optional
            The data to plot. If None, x, y, u, and v must be provided.
        x : str, list, numpy.ndarray, or xarray.DataArray, optional
            The x values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        y : str, list, numpy.ndarray, or xarray.DataArray, optional
            The y values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        u : str, list, numpy.ndarray, or xarray.DataArray, optional
            The u values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        v : str, list, numpy.ndarray, or xarray.DataArray, optional
            The v values to plot. If data is provided, this is assumed to be the
            name of a coordinate in the data. If None, data must be provided.
        style : earthkit.plots.styles.Style, optional
            The Style to use for the wind barbs. If None, a Style is automatically
            generated based on the data.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.barbs`.
        """

    block = pcolormesh

    @schema.legend.apply()
    def legend(self, style=None, location=None, **kwargs):
        """
        Add a legend to the Subplot.

        Parameters
        ----------
        style : Style, optional
            The Style to use for the legend. If None (default), a legend is
            created for each Layer with a unique Style. If a single Style is
            provided, a single legend is created based on that Style.
        location : str or tuple, optional
            The location of the legend(s). Must be a valid matplotlib location
            (see https://matplotlib.org/stable/api/_as_gen/matplotlib.pyplot.legend.html).
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.legend`.
        """
        legends = []
        if style is not None:
            dummy = [[1, 2], [3, 4]]
            mappable = self.contourf(x=dummy, y=dummy, z=dummy, style=style)
            layer = Layer(single.SingleSource(), mappable, self, style)
            legend = layer.style.legend(layer, label=kwargs.pop("label", ""), **kwargs)
            legends.append(legend)
        else:
            for i, layer in enumerate(self.distinct_legend_layers):
                if isinstance(location, (list, tuple)):
                    loc = location[i]
                else:
                    loc = location
                if layer.style is not None:
                    legend = layer.style.legend(layer, location=loc, **kwargs)
                legends.append(legend)
        return legends

    @schema.title.apply()
    def title(self, label=None, unique=True, wrap=True, capitalize=True, **kwargs):
        """
        Add a title to the plot.

        Parameters
        ----------
        label : str, optional
            The title text. If None, a default template is used. The template
            can contain metadata keys in curly braces, e.g. "{variable_name}".
        unique : bool, optional
            Whether to use unique metadata values from each Layer. If False,
            metadata values from all Layers are combined.
        wrap : bool, optional
            Whether to wrap the title text. Default is True.
        capitalize : bool, optional
            Whether to capitalize the first letter of the title. Default is True.
        **kwargs
            Additional keyword arguments to pass to `matplotlib.pyplot.title`.
        """
        if label is None:
            label = self._default_title_template
        label = self.format_string(label, unique)
        plt.sca(self.ax)
        if capitalize:
            label = label[0].upper() + label[1:]
        return plt.title(label, wrap=wrap, **kwargs)

    def format_string(self, string, unique=True, grouped=True):
        """
        Format a string with metadata from the Subplot.

        Parameters
        ----------
        string : str
            The string to format. This can contain metadata keys in curly
            braces, e.g. "{variable_name}".
        unique : bool, optional
            Whether to use unique metadata values from each Layer. If False,
            metadata values from all Layers are combined.
        grouped : bool, optional
            Whether to group metadata values from all Layers into a single
            string. If False, metadata values from each Layer are listed
            separately.
        """
        if not grouped:
            return string_utils.list_to_human(
                [LayerFormatter(layer).format(string) for layer in self.layers]
            )
        else:
            return SubplotFormatter(self, unique=unique).format(string)

    def show(self):
        """Display the plot."""
        return self.figure.show()

    def save(self, *args, **kwargs):
        """Save the plot to a file."""
        return self.figure.save(*args, **kwargs)


def thin_array(array, every=2):
    """
    Reduce the size of an array by taking every `every`th element.

    Parameters
    ----------
    array : numpy.ndarray
        The array to thin.
    every : int, optional
        The number of elements to skip.
    """
    if len(array.shape) == 1:
        return array[::every]
    else:
        return array[::every, ::every]
