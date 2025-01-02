from ..datacube_mappers import DatacubeMapper


class IrregularGridMapper(DatacubeMapper):
    # def __init__(self, base_axis, mapped_axes, resolution, local_area=[]):
    def __init__(self, base_axis, mapped_axes, resolution, md5_hash=None, local_area=[], axis_reversed=None):
        self._mapped_axes = mapped_axes
        self._base_axis = base_axis
        self._resolution = resolution
        self._axis_reversed = False
        self.compressed_grid_axes = [self._mapped_axes[1]]
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)

    def unmap(self, first_val, second_val, unmapped_idx=None):
        # TODO: But to unmap for the irregular grid, need the request tree
        # Suppose we get the idx value somehow from the tree, as an idx input
        return unmapped_idx[0]


_md5_hash = {
    0: "None",
}
