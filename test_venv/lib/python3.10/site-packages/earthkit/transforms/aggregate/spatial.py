import logging
import typing as T
from copy import deepcopy

import geopandas as gpd
import numpy as np
import pandas as pd
import xarray as xr

from earthkit.transforms.tools import (
    get_how,
    get_spatial_info,
    standard_weights,
)

logger = logging.getLogger(__name__)


def _transform_from_latlon(lat, lon):
    """
    Return an Affine transformation of input 1D arrays of lat and lon.

    This assumes that both lat and lon are regular and contiguous.

    Parameters
    ----------
    lat/lon : arrays or lists of latitude and longitude
    """
    from affine import Affine

    trans = Affine.translation(lon[0] - (lon[1] - lon[0]) / 2, lat[0] - (lat[1] - lat[0]) / 2)
    scale = Affine.scale(lon[1] - lon[0], lat[1] - lat[0])

    return trans * scale


def rasterize(
    shape_list: T.List,
    coords: xr.core.coordinates.Coordinates,
    lat_key: str = "latitude",
    lon_key: str = "longitude",
    dtype: type = int,
    **kwargs,
) -> xr.DataArray:
    """
    Rasterize a list of geometries onto the given xarray coordinates.
    This only works for regular and contiguous latitude and longitude grids.

    Parameters
    ----------
    shape_list (affine.Affine): List of geometries
    coords (xarray.coords): Coordinates of dataarray to be masked

    lat_key/lon_key: name of the latitude/longitude variables in the coordinates object

    fill: value to fill points which are not within the shape_list, default is 0
    dtype: datatype of the returned mask, default is `int`

    kwargs: Any other kwargs accepted by rasterio.features.rasterize

    Returns
    -------
    xr.DataArray
        A mask where points not inside the shape_list are set to `fill` value

    """
    from rasterio import features

    transform = _transform_from_latlon(coords[lat_key], coords[lon_key])
    out_shape = (len(coords[lat_key]), len(coords[lon_key]))
    raster = features.rasterize(shape_list, out_shape=out_shape, transform=transform, dtype=dtype, **kwargs)
    spatial_coords = {lat_key: coords[lat_key], lon_key: coords[lon_key]}
    return xr.DataArray(raster, coords=spatial_coords, dims=(lat_key, lon_key))


def mask_contains_points(shape_list, coords, lat_key="lat", lon_key="lon", **kwargs) -> xr.DataArray:
    """
    Return a mask array for the spatial points of data that lie within shapes in shape_list.
    Function uses matplotlib.Path so can accept a list of points, this is much faster than shapely.
    It was initially included for use with irregular data but has been constructed to also accept
    regular data and return in the same format as the rasterize function.

    Parameters
    ----------
    shape_list (affine.Affine): List of geometries
    coords (xarray.coords): Coordinates of dataarray to be masked

    lat_key/lon_key: name of the latitude/longitude variables in the coordinates object

    fill: value to fill points which are not within the shape_list, default is 0
    dtype: datatype of the returned mask, default is `int`

    Returns
    -------
    xr.DataArray
        A mask where points not inside the shape_list are set to `fill` value

    """
    import matplotlib.path as mpltPath

    lat_dims = coords[lat_key].dims
    lon_dims = coords[lon_key].dims
    # Assert that latitude and longitude have the same dimensions
    #   (irregular data, e.g. x,y or obs)
    # or the dimensions are themselves (regular data) but we will probably
    # just use the rasterize function for the regular case
    assert (lat_dims == lon_dims) or (lat_dims == (lat_key,) and lon_dims == (lon_key,))
    if lat_dims == (lat_key,) and lon_dims == (lon_key,):
        lon_full, lat_full = np.meshgrid(
            coords[lon_key].values,
            coords[lat_key].values,
        )
    else:
        lon_full, lat_full = (
            coords[lon_key].values,
            coords[lat_key].values,
        )
    # convert lat lon pairs to to points:
    points = list(
        zip(
            lon_full.flat,
            lat_full.flat,
        )
    )

    # get spatial dims and create output array:
    spatial_dims = list(set(lat_dims + lon_dims))
    outdata_shape = [len(coords[dim]) for dim in spatial_dims]
    outdata = np.zeros(outdata_shape).astype(bool) * np.nan
    # loop over shapes and mask any point that is in the shape
    for shape in shape_list:
        for shp in shape[0]:
            shape_exterior = shp.exterior.coords.xy
            shape_exterior = list(
                zip(
                    list(shape_exterior[0]),  # longitudes
                    list(shape_exterior[1]),  # latitudes
                )
            )
            path = mpltPath.Path(shape_exterior)
            outdata.flat[path.contains_points(points)] = True

    out_coords = {coord: coords[coord] for coord in spatial_dims}
    outarray = xr.DataArray(outdata, coords=out_coords, dims=spatial_dims)

    return outarray


def _geopandas_to_shape_list(geodataframe):
    """Iterate over rows of a geodataframe."""
    return [row[1]["geometry"] for row in geodataframe.iterrows()]


def _shape_mask_iterator(shapes, target, regular=True, **kwargs):
    """Method which iterates over shape mask methods."""
    if isinstance(shapes, gpd.GeoDataFrame):
        shapes = _geopandas_to_shape_list(shapes)
    if regular:
        mask_function = rasterize
    else:
        mask_function = mask_contains_points
    for shape in shapes:
        shape_da = mask_function([shape], target.coords, **kwargs)
        yield shape_da


def shapes_to_masks(shapes: gpd.GeoDataFrame | list[gpd.GeoDataFrame], target, regular=True, **kwargs):
    """
    Method which creates a list of masked dataarrays, if possible use the shape_mask_iterator.

    Parameters
    ----------
    shapes (gpd.GeoDataFrame | list[gpd.GeoDataFrame]): A geodataframe or list of geodataframes
        containing the polygons for masks
    target (xarray.DataArray): A dataarray to to create a mask for, only the geospatial coordinates are used

    regular (bool): If True, data is on a regular grid so use rasterize method,
        if False use mask_contains_points
    all_touched (optional):
        If True, all pixels touched by geometries will be considered in,
        if False, only pixels whose center is within. Default is False.
        Only valid for regular data.

    kwargs: kwargs accepted by the masking methods, rasterize or mask_contains_points

    Returns
    -------
    list[xr.DataArray]
        A list of masks where points inside each geometry are 1, and those outside are np.nan

    """
    if isinstance(shapes, gpd.GeoDataFrame):
        shapes = _geopandas_to_shape_list(shapes)
    if regular:
        mask_function = rasterize
    else:
        mask_function = mask_contains_points

    return [mask_function([shape], target.coords, **kwargs) for shape in shapes]


def shapes_to_mask(shapes, target, regular=True, **kwargs):
    """
    Method which creates a single masked dataarray based on all features in shapes,
        if possible use the shape_mask_iterator.

    Parameters
    ----------
    shapes (gpd.GeoDataFrame | list[gpd.GeoDataFrame]): A geodataframe or list of geodataframes
        containing the polygons for masks
    target (xarray.DataArray): A dataarray to to create a mask for, only the geospatial coordinates are used

    regular (bool): If True, data is on a regular grid so use rasterize method,
        if False use mask_contains_points
    all_touched (optional):
        If True, all pixels touched by geometries will be considered in,
        if False, only pixels whose center is within. Default is False.
        Only valid for regular data.

    kwargs: kwargs accepted by the masking methods, rasterize or mask_contains_points

    Returns
    -------
    xr.DataArray
        A mask where points inside any geometry are 1, and those outside are np.nan

    """
    if isinstance(shapes, gpd.GeoDataFrame):
        shapes = _geopandas_to_shape_list(shapes)
    if regular:
        mask_function = rasterize
    else:
        mask_function = mask_contains_points

    return mask_function(shapes, target.coords, **kwargs)


def get_mask_dim_index(
    mask_dim: str | None | T.Dict[str, T.Any],
    geodataframe: gpd.geodataframe.GeoDataFrame,
    default_index_name: str = "index",
):
    if isinstance(mask_dim, str):
        if mask_dim in geodataframe:
            mask_dim_index = pd.Index(geodataframe[mask_dim])
        else:
            mask_dim_index = geodataframe.index.rename(mask_dim)
    elif isinstance(mask_dim, dict):
        assert len(mask_dim) == 1, "If provided as a dictionary, mask_dim should have only one key value pair"
        _mask_dim, _mask_dim_values = mask_dim.items()
        mask_dim_index = pd.Index(_mask_dim_values, name=_mask_dim)
    elif mask_dim is None:
        # Use the index of the data frame
        mask_dim_index = geodataframe.index
        if mask_dim_index.name is None:
            mask_dim_index = mask_dim_index.rename(default_index_name)
    else:
        raise ValueError("Unrecognised mask_dim format")

    return mask_dim_index


def mask(
    dataarray: xr.Dataset | xr.DataArray,
    geodataframe: gpd.geodataframe.GeoDataFrame,
    lat_key: str | None = None,
    lon_key: str | None = None,
    **mask_kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Apply shape mask to some gridded data.

    The geodataframe object is treated as a single mask, any points that lie outside of any
    of the features are masked

    Parameters
    ----------
    dataarray : xr.Dataset | xr.DataArray
        Xarray data object (must have geospatial coordinates).
    geodataframe (optional): gpd.geodataframe.GeoDataFrame
        Geopandas Dataframe containing the polygons for aggregations
    lat_key/lon_key (optional): str
        key for latitude/longitude variable, default behaviour is to detect variable keys.
    all_touched (optional):
        If True, all pixels touched by geometries will be considered in,
        if False, only pixels whose center is within. Default is False.
        Only valid for regular data.

    Returns
    -------
    xr.Dataset | xr.DataArray
        A masked data array/dataset with same dimensions as the input dataarray/dataset. Any point that
        does not lie in any of the features of geodataframe is masked.

    """
    spatial_info = get_spatial_info(dataarray, lat_key=lat_key, lon_key=lon_key)
    # Get spatial info required by mask functions:
    mask_kwargs = {**mask_kwargs, **{key: spatial_info[key] for key in ["lat_key", "lon_key", "regular"]}}
    mask = shapes_to_mask(geodataframe, dataarray, **mask_kwargs)
    out = dataarray.where(mask)
    out.attrs.update(geodataframe.attrs)
    return out


def masks(
    dataarray: xr.Dataset | xr.DataArray,
    geodataframe: gpd.geodataframe.GeoDataFrame,
    mask_dim: str | None = None,
    lat_key: str | None = None,
    lon_key: str | None = None,
    chunk: bool = True,
    **mask_kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Apply multiple shape masks to some gridded data.

    Each feature in shape is treated as an individual mask to apply to
    data. The data provided is returned with an additional dimension equal in
    length to the number of features in the shape object, this can result in very
    large files which will slow down your script. It may be better to loop
    over individual features, or directly apply the mask with the shapes.reduce.

    Parameters
    ----------
    dataarray :
        Xarray data object (must have geospatial coordinates).
    geodataframe :
        Geopandas Dataframe containing the polygons for aggregations
    mask_dim (optional):
        dimension that will be created to accomodate the masked arrays, default is the index
        of the geodataframe
    all_touched (optional):
        If True, all pixels touched by geometries will be considered in,
        if False, only pixels whose center is within. Default is False.
        Only valid for regular data.
    lat_key/lon_key (optional):
        key for latitude/longitude variable, default behaviour is to detect variable keys.
    chunk : (optional) bool
        Boolean to indicate whether to use chunking, default = `True`.
        This is advised as spatial.masks can create large results. If you are working with small
        arrays, or you have implemented you own chunking rules you may wish to disable it.

    Returns
    -------
    xr.Dataset | xr.DataArray
        A masked data array with dimensions [feautre_id] + [data.dims].
        Each slice of layer corresponds to a feature in layer.

    """
    spatial_info = get_spatial_info(dataarray, lat_key=lat_key, lon_key=lon_key)
    # Get spatial info required by mask functions:
    mask_kwargs = {**mask_kwargs, **{key: spatial_info[key] for key in ["lat_key", "lon_key", "regular"]}}
    mask_dim_index = get_mask_dim_index(mask_dim, geodataframe)

    masked_arrays = []
    for mask in _shape_mask_iterator(geodataframe, dataarray, **mask_kwargs):
        this_masked_array = dataarray.where(mask)
        if chunk:
            this_masked_array = this_masked_array.chunk()
        masked_arrays.append(this_masked_array.copy())
    out = xr.concat(masked_arrays, dim=mask_dim_index.name)
    if chunk:
        out = out.chunk({mask_dim_index.name: 1})

    out = out.assign_coords({mask_dim_index.name: mask_dim_index})

    out.attrs.update(geodataframe.attrs)

    return out


def reduce(
    dataarray: xr.Dataset | xr.DataArray,
    geodataframe: gpd.GeoDataFrame | None = None,
    *args,
    **kwargs,
) -> xr.Dataset | xr.DataArray:
    """
    Apply a shape object to an xarray.DataArray object using the specified 'how' method.

    Geospatial coordinates are reduced to a dimension representing the list of features in the shape object.

    Parameters
    ----------
    dataarray :
        Xarray data object (must have geospatial coordinates).
    geodataframe :
        Geopandas Dataframe containing the polygons for aggregations
    how (optional):
        method used to apply mask. Default='mean', which calls np.nanmean
    weights (optional):
        Provide weights for aggregation, also accepts recognised keys for weights, e.g.
        'latitude'
    lat_key/lon_key (optional):
        key for latitude/longitude variable, default behaviour is to detect variable keys.
    extra_reduce_dims (optional):
        any additional dimensions to aggregate over when reducing over spatial dimensions
    mask_dim (optional):
        dimension that will be created after the reduction of the spatial dimensions, default is the index
        of the dataframe
    all_touched (optional):
        If True, all pixels touched by geometries will be considered in,
        if False, only pixels whose center is within. Default is False.
        Only valid for regular data.
    mask_kwargs (optional):
        Any kwargs to pass into the mask method
    return_as (optional):
        what format to return the data object, `pandas` or `xarray`. Work In Progress
    how_label (optional):
        label to append to variable name in returned object, default is not to append
    kwargs (optional):
        kwargs recognised by the how function

    Returns
    -------
    xr.Dataset | xr.DataArray
        A data array with dimensions `features` + `data.dims not in 'lat','lon'`.
        Each slice of layer corresponds to a feature in layer.

    """
    if isinstance(dataarray, xr.Dataset):
        return_as: str = kwargs.get("return_as", "xarray")
        if return_as in ["xarray"]:
            out_ds = xr.Dataset().assign_attrs(dataarray.attrs)
            for var in dataarray.data_vars:
                out_da = _reduce_dataarray(dataarray[var], geodataframe=geodataframe, *args, **kwargs)
                out_ds[out_da.name] = out_da
            return out_ds
        elif "pandas" in return_as:
            logger.warn(
                "Returning reduced data in pandas format is considered experimental and may change in future"
                "versions of earthkit"
            )
            if geodataframe is not None:
                out = geodataframe
                for var in dataarray.data_vars:
                    out = _reduce_dataarray(dataarray[var], geodataframe=out, *args, **kwargs)
            else:
                out = None
                for var in dataarray.data_vars:
                    _out = _reduce_dataarray(dataarray[var], *args, **kwargs)
                    if out is None:
                        out = _out
                    else:
                        out = pd.merge(out, _out)
            return out
        else:
            raise TypeError("Return as type not recognised or incompatible with inputs")
    else:
        return _reduce_dataarray(dataarray, geodataframe=geodataframe, *args, **kwargs)


def _reduce_dataarray(
    dataarray: xr.DataArray,
    geodataframe: gpd.GeoDataFrame | None = None,
    pd_dataframe: pd.DataFrame | None = None,
    how: T.Callable | str = "mean",
    weights: None | str | np.ndarray = None,
    lat_key: str | None = None,
    lon_key: str | None = None,
    extra_reduce_dims: list | str = [],
    mask_dim: str | None = None,
    return_as: str = "xarray",
    how_label: str | None = None,
    squeeze: bool = True,
    all_touched: bool = False,
    mask_kwargs: dict[str, T.Any] = dict(),
    return_geometry_as_coord: bool = False,
    **reduce_kwargs,
) -> xr.DataArray | pd.DataFrame:
    """
    Reduce an xarray.DataArray object over its geospatial dimensions using the specified 'how' method.

    If a geodataframe is provided the DataArray is reduced over each feature in the geodataframe.
    Geospatial coordinates are reduced to a dimension representing the list of features in the shape object.

    Parameters
    ----------
    dataarray :
        Xarray data object (must have geospatial coordinates).
    geodataframe (optional):
        Geopandas Dataframe containing the polygons for aggregations
    how (optional):
        method used to apply mask. Default='mean', which calls np.nanmean
    weights (optional):
        Provide weights for aggregation, also accepts recognised keys for weights, e.g.
        'latitude'
    lat_key/lon_key (optional):
        key for latitude/longitude variable, default behaviour is to detect variable keys.
    extra_reduce_dims (optional):
        any additional dimensions to aggregate over when reducing over spatial dimensions
    mask_dim (optional):
        dimension that will be created after the reduction of the spatial dimensions, default = `"FID"`
    return_as (optional):
        what format to return the data object, `"pandas"` or `"xarray"`. Work In Progress
    how_label (optional):
        label to append to variable name in returned object, default is `how`
    mask_kwargs (optional):
        Any kwargs to pass into the mask method
    reduce_kwargs (optional):
        kwargs recognised by the how function
    return_geometry_as_coord (optional):
        include the geometries as a coordinate in the returned xarray object. WARNING: geometries are not
        serialisable objects, therefore this xarray will not be saveable as netCDF.

    Returns
    -------
    xr.Dataset | xr.DataArray | pd.DataFrame
        A data array with dimensions [features] + [data.dims not in ['lat','lon']].
        Each slice of layer corresponds to a feature in layer

    """
    extra_out_attrs = {}
    how_str: None | str = None
    if weights is None:
        # convert how string to a method to apply
        if isinstance(how, str):
            how_str = deepcopy(how)
            how = get_how(how)
        assert isinstance(how, T.Callable), f"how must be a callable: {how}"
        if how_str is None:
            # get label from how method
            how_str = how.__name__
    else:
        # Create any standard weights, e.g. latitude.
        # TODO: handle kwargs better, currently only lat_key is accepted
        if isinstance(weights, str):
            weights = standard_weights(dataarray, weights, lat_key=lat_key)
        # We ensure the callable is a string
        if callable(how):
            how = how.__name__
        if how_str is None:
            how_str = how

    how_str = how_str or how_label
    new_long_name_components = [
        comp for comp in [how_str, dataarray.attrs.get("long_name", dataarray.name)] if comp is not None
    ]
    new_long_name = " ".join(new_long_name_components)
    new_short_name_components = [comp for comp in [dataarray.name, how_label] if comp is not None]
    new_short_name = "_".join(new_short_name_components)

    if isinstance(extra_reduce_dims, str):
        extra_reduce_dims = [extra_reduce_dims]

    spatial_info = get_spatial_info(dataarray, lat_key=lat_key, lon_key=lon_key)
    # Get spatial info required by mask functions:
    mask_kwargs = {**mask_kwargs, **{key: spatial_info[key] for key in ["lat_key", "lon_key", "regular"]}}
    # All touched only valid for rasterize method
    if spatial_info["regular"]:
        mask_kwargs.setdefault("all_touched", all_touched)
    else:
        if all_touched:
            logger.warning("all_touched only valid for regular data, ignoring")
    spatial_dims = spatial_info.get("spatial_dims")

    reduce_dims = spatial_dims + extra_reduce_dims
    extra_out_attrs.update({"reduce_dims": reduce_dims})
    reduce_kwargs.update({"dim": reduce_dims})
    reduced_list = []

    # If not using mask, then create a dummy mask:
    if geodataframe is None:
        masks = [dataarray]
    else:
        masks = _shape_mask_iterator(geodataframe, dataarray, **mask_kwargs)

    for mask in masks:
        this = dataarray.where(mask, other=np.nan)

        # If weighted, use xarray weighted arrays which correctly handle missing values etc.
        if weights is not None:
            this = this.weighted(weights)
            reduced_list.append(this.__getattribute__(how)(**reduce_kwargs))
        else:
            reduced = this.reduce(how, **reduce_kwargs).compute()
            reduced = reduced.assign_attrs(dataarray.attrs)
            reduced_list.append(reduced)

    if squeeze:
        reduced_list = [red_data.squeeze() for red_data in reduced_list]

    # If no geodataframe, there is just one reduced array
    if geodataframe is None:
        out_xr = reduced_list[0]
    else:
        mask_dim_index = get_mask_dim_index(mask_dim, geodataframe)
        out_xr = xr.concat(reduced_list, dim=mask_dim_index)

    out_xr = out_xr.rename(new_short_name)

    if "pandas" in return_as:
        reduce_attrs = {
            f"{dataarray.name}": dataarray.attrs,
            f"{new_short_name}": {
                "long_name": new_long_name,
                "units": dataarray.attrs.get("units", "No units found"),
                **extra_out_attrs,
            },
        }

        if geodataframe is None:
            # If no geodataframe, then just convert xarray to dataframe
            out = out_xr.to_dataframe()
        else:
            # Otherwise, splice the geodataframe and reduced xarray
            reduce_attrs = {
                **geodataframe.attrs.get("reduce_attrs", {}),
                **reduce_attrs,
            }
            out = geodataframe.set_index(mask_dim_index)
            if return_as in ["pandas"]:  # Return as a fully expanded pandas.DataFrame
                # Convert to DataFrame
                out = out.join(out_xr.to_dataframe())
            elif return_as in ["pandas_compact"]:
                # add the reduced data into a new column as a numpy array,
                # store the dim information in the attributes

                out_dims = {
                    dim: dataarray.coords.get(dim).values if dim in dataarray.coords else None
                    for dim in reduced_list[0].dims
                }
                reduce_attrs[f"{new_short_name}"].update({"dims": out_dims})
                reduced_list = [red.values for red in reduced_list]
                out = out.assign(**{new_short_name: reduced_list})
        out.attrs.update({"reduce_attrs": reduce_attrs})
    else:
        if geodataframe is not None:
            if return_geometry_as_coord:
                out_xr = out_xr.assign_coords(
                    **{
                        "geometry": (mask_dim, [geom for geom in geodataframe["geometry"]]),
                    }
                )
            out_xr = out_xr.assign_attrs({**geodataframe.attrs, **extra_out_attrs})
        out = out_xr

    return out
