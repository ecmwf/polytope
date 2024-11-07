import cartopy.crs as ccrs
import numpy as np
from scipy.interpolate import NearestNDInterpolator


def nnshow(var, x, y, nx=1000, ny=1000, ax=None, style=None, **kwargs):
    """"""
    xlims = ax.get_xlim()
    ylims = ax.get_ylim()
    # NOTE: we want the center coordinate of each pixel, thus we have to
    # compute the linspace over halve a pixel size less than the plot's limits
    dx = (xlims[1] - xlims[0]) / nx
    dy = (ylims[1] - ylims[0]) / ny
    xvals = np.linspace(xlims[0] + dx / 2, xlims[1] - dx / 2, nx)
    yvals = np.linspace(ylims[0] + dy / 2, ylims[1] - dy / 2, ny)
    xvals2, yvals2 = np.meshgrid(xvals, yvals)

    latlon = ccrs.PlateCarree().transform_points(
        ax.projection, xvals2, yvals2, np.zeros_like(xvals2)
    )

    lon = latlon[:, :, 0]
    lat = latlon[:, :, 1]

    if len(x.shape) > 1:
        x = x.flatten()
        y = y.flatten()

    # x, y = np.meshgrid(x, y)
    interp = NearestNDInterpolator(list(zip(x, y)), var.flatten())
    # interp = RegularGridInterpolator((x, y), var)

    zvals = interp(lon, lat)

    if style is not None:
        kwargs = {**kwargs, **style.to_pcolormesh_kwargs(zvals)}

    return ax.imshow(zvals, extent=xlims + ylims, origin="lower", **kwargs)
