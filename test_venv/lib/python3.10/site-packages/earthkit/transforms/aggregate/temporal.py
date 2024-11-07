import logging
import typing as T

import numpy as np
import pandas as pd
import xarray as xr

from earthkit.transforms import tools
from earthkit.transforms.aggregate.general import how_label_rename, resample
from earthkit.transforms.aggregate.general import reduce as _reduce
from earthkit.transforms.aggregate.general import rolling_reduce as _rolling_reduce
from earthkit.transforms.tools import groupby_time

logger = logging.getLogger(__name__)


def standardise_time(
    dataarray: xr.Dataset | xr.DataArray,
    target_format: str = "%Y-%m-%d %H:%M:%S",
) -> xr.Dataset | xr.DataArray:
    """
    Convert time coordinates to a standard format using the Gregorian calendar.

    This function is helpful when combining data from different sources with
    different time standards or calendars - for example, when combining data
    which uses a 360-day calendar with data which uses a Gregorian calendar. All
    data passed into this function will be converted to a standard Gregorian
    calendar format.

    Parameters
    ----------
    dataarray : xr.Dataset or xr.DataArray
        Data object with a time coordinate to be standardised.
    target_format : str, optional
        Datetime format to use when creating the standardised datetime object.
        This can be used to change the resolution of the datetime object - for
        example, "%Y-%m-%d" will reduce to daily resolution - or to fix elements
        of the datetime object - for example, "%Y-%m-15" would reduce to monthly
        resolution and fix the date to the 15th of each month.

    Returns
    -------
    xr.Dataset | xr.DataArray
        Data object with the time coordinate standardised to the specified format

    """
    try:
        source_times = [time_value.strftime(target_format) for time_value in dataarray.time.values]
    except AttributeError:
        source_times = [
            pd.to_datetime(time_value).strftime(target_format) for time_value in dataarray.time.values
        ]

    standardised_times = np.array(
        [pd.to_datetime(time_string).to_datetime64() for time_string in source_times]
    )

    dataarray = dataarray.assign_coords({"time": standardised_times})

    history = dataarray.attrs.get("history", "")
    history += (
        "The time coordinate of this data has been standardised with "
        "earthkit.transforms.aggregate.temporal.standardise_time."
    )
    dataarray = dataarray.assign_attrs({"history": history})

    return dataarray


@tools.time_dim_decorator
def reduce(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    time_dim: str | None = None,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Reduce an xarray.dataarray or xarray.dataset along the time/date dimension using a specified `how` method.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    how: str or callable
        Method used to reduce data. Default='mean', which will implement the xarray in-built mean.
        If string, it must be an in-built xarray reduce method, a earthkit how method or any numpy method.
        In the case of duplicate names, method selection is first in the order: xarray, earthkit, numpy.
        Otherwise it can be any function which can be called in the form `f(x, axis=axis, **kwargs)`
        to return the result of reducing an np.ndarray over an integer valued axis
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _{how}
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray reduced in the time dimension using the specified method

    """
    if "frequency" in kwargs:
        return resample(dataarray, *args, time_dim=time_dim, **kwargs)

    reduce_dims = tools.ensure_list(kwargs.get("dim", []))
    if time_dim is not None and time_dim not in reduce_dims:
        reduce_dims.append(time_dim)
    kwargs["dim"] = reduce_dims

    return _reduce(dataarray, *args, **kwargs)


def mean(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the mean of an xarray.dataarray or xarray.dataset along the time/date dimension.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _mean
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray of the mean value in the time dimensions

    """
    kwargs["how"] = "mean"
    return reduce(dataarray, *args, **kwargs)


def median(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the median of an xarray.dataarray or xarray.dataset along the time/date dimension.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _mean
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray of the median value in the time dimensions

    """
    kwargs["how"] = "median"
    return reduce(dataarray, *args, **kwargs)


def min(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the mn of an xarray.dataarray or xarray.dataset along the time/date dimension.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _mean
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray of the minimum value in the time dimensions

    """
    kwargs["how"] = "min"
    return reduce(dataarray, *args, **kwargs)


def max(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the max of an xarray.dataarray or xarray.dataset along the time/date dimension.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _mean
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray of the maximum value in the time dimensions

    """
    kwargs["how"] = "max"
    return reduce(dataarray, *args, **kwargs)


def std(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Calculate the standard deviation of an xarray.dataarray or xarray.dataset along the time/date dimension.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _mean
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray of the standard deviation in the time dimensions

    """
    kwargs["how"] = "std"
    return reduce(dataarray, *args, **kwargs)


def sum(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Calculate the standard deviation of an xarray.dataarray or xarray.dataset along the time/date dimension.

    With the option to apply weights either directly or using a specified
    `weights` method.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data object to reduce
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
        If you do not want to aggregate along the time dimension use earthkit.transforms.aggregate.reduce
    weights : str
        Choose a recognised method to apply weighting. Currently available methods are; 'latitude'
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _mean
    how_dropna : str
        Choose how to drop nan values.
        Default is None and na values are preserved. Options are 'any' and 'all'.
    **kwargs :
        kwargs recognised by the how :func: `earthkit.transforms.aggregate.reduce`

    Returns
    -------
    xr.Dataset | xr.DataArray
        A dataarray summed in the time dimensions


    """
    kwargs["how"] = "sum"
    return reduce(dataarray, *args, **kwargs)


@tools.time_dim_decorator
def daily_reduce(
    dataarray: xr.Dataset | xr.DataArray,
    how: str | T.Callable = "mean",
    time_dim: str | None = None,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Group data by day and reduce using the given how method.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    how: str or callable
        Method used to reduce data. Default='mean', which will implement the xarray in-built mean.
        If string, it must be an in-built xarray reduce method, a earthkit how method or any numpy method.
        In the case of duplicate names, method selection is first in the order: xarray, earthkit, numpy.
        Otherwise it can be any function which can be called in the form `f(x, axis=axis, **kwargs)`
        to return the result of reducing an np.ndarray over an integer valued axis
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _daily_{how}
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily values using the specified method
    """
    # If time_dim in dimensions then use resample, this should be faster.
    #  At present, performance differences are small, but resampling can be improved by handling as
    #  a pandas dataframes. resample function should be updated to do this.
    #  NOTE: force_groupby is an intentionally undocumented kwarg for debug purposes
    if time_dim in dataarray.dims and not kwargs.pop("force_groupby", False):
        kwargs.setdefault("frequency", "D")
        red_array = resample(dataarray, time_dim=time_dim, how=how, **kwargs)
    else:
        # Otherwise, we groupby, with specifics set up for daily and handling both datetimes and timedeltas
        if dataarray[time_dim].dtype in ["<M8[ns]"]:  # datetime
            group_key = "date"
        elif dataarray[time_dim].dtype in ["<m8[ns]"]:  # timedelta
            group_key = "days"
        else:
            raise TypeError(f"Invalid type for time dimension ({time_dim}): {dataarray[time_dim].dtype}")

        grouped_data = groupby_time(dataarray, time_dim=time_dim, frequency=group_key)
        # If how is string and inbuilt method of grouped_data, we apply
        if isinstance(how, str) and how in dir(grouped_data):
            red_array = grouped_data.__getattribute__(how)(**kwargs)
        else:
            # If how is string, fetch function from dictionary:
            if isinstance(how, str):
                how = tools.get_how(how)
            assert isinstance(how, T.Callable), f"how method not recognised: {how}"

            red_array = grouped_data.reduce(how, **kwargs)
        try:
            red_array[group_key] = pd.DatetimeIndex(red_array[group_key].values)
        except TypeError:
            logger.warning(f"Failed to convert {group_key} to datetime, it may already be a datetime object")

        red_array = how_label_rename(red_array, kwargs.get("how_label"))

    return red_array


def daily_mean(dataarray: xr.Dataset | xr.DataArray, *args, **kwargs) -> xr.Dataset | xr.DataArray:
    """
    Return the daily mean of the datacube.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily mean values
    """
    return daily_reduce(dataarray, *args, how="mean", **kwargs)


def daily_median(dataarray: xr.Dataset | xr.DataArray, *args, **kwargs):
    """
    Return the daily median of the datacube.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily median values
    """
    return daily_reduce(dataarray, *args, how="median", **kwargs)


def daily_max(dataarray: xr.Dataset | xr.DataArray, *args, **kwargs):
    """
    Calculate the daily maximum.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily max values
    """
    return daily_reduce(dataarray, *args, how="max", **kwargs)


def daily_min(dataarray: xr.Dataset | xr.DataArray, *args, **kwargs):
    """
    Calculate the daily minimum.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily min values
    """
    return daily_reduce(dataarray, *args, how="min", **kwargs)


def daily_std(dataarray: xr.Dataset | xr.DataArray, *args, **kwargs):
    """
    Calculate the daily standard deviation.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily standard deviation values
    """
    return daily_reduce(dataarray, *args, how="std", **kwargs)


def daily_sum(dataarray: xr.Dataset | xr.DataArray, *args, **kwargs):
    """
    Calculate the daily sum (accumulation).

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to daily sum values
    """
    return daily_reduce(dataarray, *args, how="sum", **kwargs)


@tools.time_dim_decorator
def monthly_reduce(
    dataarray: xr.Dataset | xr.DataArray,
    how: str | T.Callable = "mean",
    time_dim: str | None = None,
    **kwargs,
):
    """
    Group data by day and reduce using the given how method.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    how: str or callable
        Method used to reduce data. Default='mean', which will implement the xarray in-built mean.
        If string, it must be an in-built xarray reduce method, a earthkit how method or any numpy method.
        In the case of duplicate names, method selection is first in the order: xarray, earthkit, numpy.
        Otherwise it can be any function which can be called in the form `f(x, axis=axis, **kwargs)`
        to return the result of reducing an np.ndarray over an integer valued axis
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    how_label : str
        Label to append to the name of the variable in the reduced object, default is _monthly_{how}

    **kwargs
        Keyword arguments to be passed to :func:`reduce`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly values using the specified method
    """
    # If time_dim in dimensions then use resample, this should be faster.
    #  At present, performance differences are small, but resampling can be improved by handling as
    #  a pandas dataframes. reample function should be updated to do this.
    #  NOTE: force_groupby is an undocumented kwarg for debug purposes
    if time_dim in dataarray.dims and not kwargs.pop("force_groupby", False):
        kwargs.setdefault("frequency", "MS")
        red_array = resample(dataarray, time_dim=time_dim, how=how, **kwargs)
    else:
        # Otherwise, we groupby, with specifics set up for monthly and handling both datetimes and timedeltas
        if dataarray[time_dim].dtype in ["<M8[ns]"]:  # datetime
            # create a year-month coordinate
            years = dataarray[f"{time_dim}.year"]
            months = dataarray[f"{time_dim}.month"]
            dataarray.coords["year_months"] = years * 100 + months
            # Group by this:
            grouped_data = dataarray.groupby("year_months")
        elif dataarray[time_dim].dtype in ["<m8[ns]"]:  # timedelta
            raise TypeError(
                "Monthly aggregation is not support for timedelta objects. "
                "Please choose an alternative coordinate, or convert dimension to datatime object"
            )
        else:
            raise TypeError(f"Invalid type for time dimension ({time_dim}): {dataarray[time_dim].dtype}")

        # If how is string and inbuilt method of grouped_data, we apply
        if isinstance(how, str) and how in dir(grouped_data):
            red_array = grouped_data.__getattribute__(how)(**kwargs)
        else:
            # If how is string, fetch function from dictionary:
            if isinstance(how, str):
                how = tools.get_how(how)
            assert isinstance(how, T.Callable), f"how method not recognised: {how}"

            red_array = grouped_data.reduce(how, **kwargs)
        # Remove the year_months coordinate
        del red_array["year_months"]

        red_array = how_label_rename(red_array, kwargs.get("how_label"))

    return red_array


def monthly_mean(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the monthly mean.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`resample`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly mean values
    """
    return monthly_reduce(dataarray, *args, how="mean", **kwargs)


def monthly_median(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the monthly median.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`resample`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly median values
    """
    return monthly_reduce(dataarray, *args, how="median", **kwargs)


def monthly_min(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the monthly min.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`resample`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly minimum values
    """
    return monthly_reduce(dataarray, *args, how="min", **kwargs)


def monthly_max(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the monthly max.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`resample`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly maximum values
    """
    return monthly_reduce(dataarray, *args, how="max", **kwargs)


def monthly_std(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the monthly standard deviation.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`resample`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly standard deviation values
    """
    return monthly_reduce(dataarray, *args, how="std", **kwargs)


def monthly_sum(
    dataarray: xr.Dataset | xr.DataArray,
    *args,
    **kwargs,
):
    """
    Calculate the monthly sum/accumulation along the time dimension.

    Parameters
    ----------
    dataarray : xr.DataArray
        DataArray containing a `time` dimension.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object to use for the calculation,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    time_shift : (optional) None, timedelta or dict
        A time shift to apply to the data prior to calculation, e.g. to change the local time zone.
        It can be provided as any object that can be understood by `pandas.Timedelta`, a dictionary is passed
        as kwargs to `pandas.Timedelta`. Default is None.
    remove_partial_periods : bool
        If True and a time_shift has been applied, the first and last time steps are removed to ensure
        equality in sampling periods. Default is False.
    **kwargs
        Keyword arguments to be passed to :func:`resample`.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced to monthly sum values
    """
    return monthly_reduce(dataarray, *args, how="sum", **kwargs)


@tools.time_dim_decorator
def rolling_reduce(
    dataarray: xr.Dataset | xr.DataArray,
    window_length: int | None = None,
    time_dim: str | None = None,
    **kwargs,
):
    """Return reduced data using a moving window over the time dimension.

    Parameters
    ----------
    dataarray : xr.DataArray or xr.Dataset
        Data over which the moving window is applied according to the reduction method.
    window_length :
        Length of window for the rolling groups along the time dimension.
        **see documentation for xarray.dataarray.rolling**.
    time_dim : str
        Name of the time dimension, or coordinate, in the xarray object,
        default behaviour is to deduce time dimension from
        attributes of coordinates, then fall back to `"time"`.
    min_periods : integer
        The minimum number of observations in the window required to have a value
        (otherwise result is NaN). Default is to set **min_periods** equal to the size of the window.
        **see documentation for xarray.dataarray.rolling**
    center : bool
        Set the labels at the centre of the window, **see documentation for xarray.dataarray.rolling**.
    how_reduce : str,
        Function to be applied for reduction. Default is 'mean'.
    how_dropna : str
        Determine if dimension is removed from the output when we have at least one NaN or
        all NaN. **how_dropna** can be 'None', 'any' or 'all'. Default is 'any'.
    windows : dict[str, int]
        Any other windows to apply to other dimensions in the dataset/dataarray
    **kwargs :
        Any kwargs that are compatible with the select `how_reduce` method.

    Returns
    -------
    xr.DataArray | xr.Dataset
        A dataarray reduced values with a rolling window applied along the time dimension.
    """
    if window_length is not None:
        kwargs.update({time_dim: window_length})
    return _rolling_reduce(dataarray, **kwargs)
