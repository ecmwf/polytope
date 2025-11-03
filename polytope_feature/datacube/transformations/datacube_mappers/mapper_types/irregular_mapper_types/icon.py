from eckit.geo import Grid

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
    ):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = False
        self.compressed_grid_axes = [self._mapped_axes[1]]
        self.uuid = mapper_options.uuid
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(self.uuid, None)

        self.is_irregular = True

    def grid_latlon_points(self):

        grid = Grid({"grid": self.uuid})

        latlons = grid.to_latlons()
        latitudes = latlons[0]
        longitudes = latlons[1]

        points = list(zip(latitudes, longitudes))
        return points


_md5_hash = {}
