import math
import os

import requests
import xarray as xr

from ......utility.exceptions import HTTPError
from ..irregular import IrregularGridMapper


class ICONGridMapper(IrregularGridMapper):
    def __init__(
        self,
        base_axis,
        mapped_axes,
        resolution,
        md5_hash=None,
        local_area=[],
        axis_reversed=None,
        mapper_options=None,
        grid_online_path=None,
        grid_local_directory=None,
    ):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = False
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)

        self.uuid = mapper_options.uuid
        self.is_irregular = True
        self.grid_online_path = grid_online_path
        self.grid_local_directory = grid_local_directory
        self.uuid_map = {"icon_grid_0026_R03B07_G": "icon_grid_0026_R03B07_G.nc"}

    def get_icon_grid_path(self, filename):
        script_dir = self.grid_local_directory

        local_directory = os.path.join(script_dir, "icon_grids")

        if not os.path.exists(local_directory):
            os.makedirs(local_directory)

        # Construct the full path for the local file
        local_file_path = os.path.join(local_directory, filename)

        if not os.path.exists(local_file_path):
            session = requests.Session()
            response = session.get(self.grid_online_path)
            if response.status_code != 200:
                raise HTTPError(response.status_code, "Failed to download data.")
            # Save the downloaded data to the local file
            with open(local_file_path, "wb") as f:
                f.write(response.content)
        return local_file_path

    def grid_latlon_points(self):
        path = self.uuid_map[self.uuid]

        # if the path already exists locally, then do nothing
        # else, pull data from remote

        path = self.get_icon_grid_path(path)

        grid = xr.open_dataset(path, engine="netcdf4")

        longitudes = grid.clon.values * 180 / math.pi
        latitudes = grid.clat.values * 180 / math.pi

        points = list(zip(latitudes, longitudes))
        return points


_md5_hash = {}
