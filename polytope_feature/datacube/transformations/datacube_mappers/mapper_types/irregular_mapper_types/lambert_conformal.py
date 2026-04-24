from polytope_feature.polytope_rs import get_latlons_oblate, get_latlons_sphere

from ...datacube_mappers import DatacubeMapper


class LambertConformalGridMapper(DatacubeMapper):
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
        if md5_hash is not None:
            self.md5_hash = md5_hash
        else:
            self.md5_hash = _md5_hash.get(resolution, None)

        self.is_spherical = mapper_options.is_spherical
        self.is_irregular = True

        if self.is_spherical:
            self.radius = mapper_options.radius
        else:
            self.earthMinorAxisInMetres = mapper_options.earthMinorAxisInMetres
            self.earthMajorAxisInMetres = mapper_options.earthMajorAxisInMetres

        self.nv = mapper_options.nv
        self.nx = mapper_options.nx
        self.ny = mapper_options.ny
        self.LoVInDegrees = mapper_options.LoVInDegrees
        self.Dx = mapper_options.Dx
        self.Dy = mapper_options.Dy
        self.latFirstInRadians = mapper_options.latFirstInRadians
        self.lonFirstInRadians = mapper_options.lonFirstInRadians
        self.LoVInRadians = mapper_options.LoVInRadians
        self.Latin1InRadians = mapper_options.Latin1InRadians
        self.Latin2InRadians = mapper_options.Latin2InRadians
        self.LaDInRadians = mapper_options.LaDInRadians

    def grid_latlon_points(self):
        if self.is_spherical:
            return get_latlons_sphere(
                self.Latin1InRadians,
                self.Latin2InRadians,
                self.radius,
                self.latFirstInRadians,
                self.LaDInRadians,
                self.lonFirstInRadians,
                self.LoVInRadians,
                self.ny,
                self.nx,
                self.Dy,
                self.Dx,
            )
        else:
            return get_latlons_oblate(
                self.Latin1InRadians,
                self.Latin2InRadians,
                self.earthMinorAxisInMetres,
                self.earthMajorAxisInMetres,
                self.latFirstInRadians,
                self.LaDInRadians,
                self.lonFirstInRadians,
                self.LoVInRadians,
                self.ny,
                self.nx,
                self.Dy,
                self.Dx,
            )


_md5_hash = {}
