from ..irregular import IrregularGridMapper


class UnstructuredGridMapper(IrregularGridMapper):
    def __init__(
        self, base_axis, mapped_axes, resolution, md5_hash=None, local_area=[], axis_reversed=None, mapper_options=None, grid_online_path=None,
        grid_local_directory=None
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

        self.latlon_points = mapper_options.points
        self.is_irregular = True

    def grid_latlon_points(self):
        return self.latlon_points


_md5_hash = {}
