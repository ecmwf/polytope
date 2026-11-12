"""A minimal, slicing-only `Datacube` for a grid that has no backing data.

`retrieve_interpolated()` needs to run Polytope's normal slicing mechanism
(hullslicer/quadtree/point-in-polygon, for *any* shape: Box, Disk, Polygon,
Path, Union, ...) against the *output* grid, to find out exactly which
output grid points a request's lat/lon shape(s) select - not just a bounding
box. This class provides just enough of the `Datacube` interface to do that,
by reusing the same "mapper" axis-transformation machinery the real (input)
datacube uses for its own lat/lon axes, configured for the output grid
instead.

It is never used for `.get()` - only for `Polytope.slice()`.
"""

from __future__ import annotations

from ..utility.geometry import nearest_pt
from .backends.datacube import Datacube


def _find_grid_axis_options(axis_options):
    """Find the AxisConfig entry holding the "mapper" transformation, and the
    final (lat, lon) axis names it maps to.
    """
    for opt in axis_options:
        for transform in opt.transformations:
            if getattr(transform, "name", None) == "mapper":
                return opt, list(transform.axes)
    raise ValueError("Could not find a 'mapper' axis transformation in the datacube's axis options")


def build_output_grid_axis_options(datacube, out_grid_desc):
    """Build the (deep-copied) axis option list for an output grid datacube:
    the same "mapper" axis config as the real (input) datacube, but with its
    type/resolution swapped for the output grid's, plus any other axis
    options that apply directly to the grid's lat/lon axes (eg. "reverse" on
    latitude, "cyclic" on longitude) - unchanged, since those conventions are
    grid-independent.
    """
    mapper_opt, grid_axes = _find_grid_axis_options(datacube.axis_options)

    mapper_opt_copy = mapper_opt.model_copy(deep=True)
    for transform in mapper_opt_copy.transformations:
        if getattr(transform, "name", None) == "mapper":
            transform.type = out_grid_desc["type"]
            transform.resolution = out_grid_desc.get("resolution")
            transform.md5_hash = None

    other_opts = [opt.model_copy(deep=True) for opt in datacube.axis_options if opt.axis_name in grid_axes]
    return [mapper_opt_copy] + other_opts, tuple(grid_axes)


class OutputGridDatacube(Datacube):
    """Slicing-only datacube exposing just the (lat, lon) axes of an output grid."""

    def __init__(self, axis_options):
        super().__init__(axis_options=axis_options, compressed_axes_options=[])
        self._axes = {}
        self.treated_axes = []
        self.complete_axes = []
        self.grid_transformation = None
        self.nearest_search = {}

        mapper_opt, grid_axes = _find_grid_axis_options(axis_options)
        self._check_and_add_axes(mapper_opt, mapper_opt.axis_name, [])
        self.treated_axes.append(mapper_opt.axis_name)
        self.complete_axes.append(mapper_opt.axis_name)

        # Mirrors FDBDatacube's second pass: apply any remaining axis-specific
        # options (eg. "reverse"/"cyclic") to the axes the mapper just created.
        # Note: these axes are deliberately *not* added to treated_axes/complete_axes,
        # matching FDBDatacube's own behaviour (axis.find_modified_indexes() relies on
        # that to know whether to treat its incoming `indexes` as already-ordered data,
        # which doesn't apply here since the mapper transformation fully overrides them).
        for name in list(self._axes.keys()):
            if name not in self.treated_axes:
                opt = next((o for o in axis_options if o.axis_name == name), None)
                val = self._axes[name].type
                self._check_and_add_axes(opt, name, val)

        # Always compressible: lets orthogonal (eg. Box) shapes produce compact
        # multi-value tree nodes instead of one node per point.
        self.compressed_axes = list(grid_axes)

    def get(self, requests, context=None):
        raise NotImplementedError("OutputGridDatacube is only used for slicing, never for data retrieval")

    def find_point_cloud(self):
        if self.grid_transformation is not None and self.grid_transformation.is_irregular:
            return self.grid_transformation._final_transformation.grid_latlon_points()
        return None

    def select(self, path, unmapped_path):
        # Never actually used: the "mapper" transformation's find_modified_indexes()
        # fully overrides the (lat, lon) axes' candidate indexes without consulting this.
        return {}

    def datacube_natural_indexes(self, axis, subarray):
        return subarray.get(axis.name, None) if hasattr(subarray, "get") else None

    def nearest_lat_lon_search(self, requests):
        """Resolve `method="nearest"` lat/lon shapes against the sliced tree.

        Self-contained port of `FDBDatacube.nearest_lat_lon_search` (it only
        needs the tree, `self.nearest_search` and `self.grid_transformation`,
        none of which are FDB-specific).
        """
        if len(self.nearest_search) == 0:
            return None
        first_ax_name = requests.children[0].axis.name
        second_ax_name = requests.children[0].children[0].axis.name

        axes_in_nearest_search = [
            first_ax_name not in self.nearest_search.keys(),
            second_ax_name not in self.nearest_search.keys(),
        ]
        if all(not item for item in axes_in_nearest_search):
            raise Exception("nearest point search axes are wrong")

        second_ax = requests.children[0].children[0].axis

        nearest_pts_k = self.nearest_search.get((first_ax_name, second_ax_name), None)
        if nearest_pts_k is not None:
            query_points = nearest_pts_k[0]
        else:
            nearest_pts_k = self.nearest_search.get((second_ax_name, first_ax_name), None)
            query_points = [[pt[1], pt[0]] for pt in nearest_pts_k[0]]
        query_tags = nearest_pts_k[2] if len(nearest_pts_k) > 2 else [None] * len(query_points)

        k = nearest_pts_k[1]
        if k != 1 and not self.grid_transformation.is_irregular:
            k = 1

        transformed_nearest_pts = []
        for point in query_points:
            transformed_nearest_pts.append([point[0], second_ax._remap_val_to_axis_range(point[1])])

        found_latlon_pts = []
        for lat_child in requests.children:
            for lon_child in lat_child.children:
                found_latlon_pts.append([lat_child.values, lon_child.values])

        nearest_latlons = []
        point_tags = {}
        for pt, tag in zip(transformed_nearest_pts, query_tags):
            nearest_latlon = nearest_pt(found_latlon_pts, pt, k)
            nearest_latlons.extend(nearest_latlon)
            for latlon in nearest_latlon:
                tags = point_tags.setdefault(tuple(latlon), set())
                if tag is not None:
                    tags.add(tag)

        lat_children_by_values = {child.values: child for child in requests.children}
        lat_children_values = list(lat_children_by_values.keys())
        for lat_child_val in lat_children_values:
            lat_child = lat_children_by_values[lat_child_val]
            if lat_child.values not in [(latlon[0],) for latlon in nearest_latlons]:
                lat_child.remove_branch()
            else:
                possible_lons = [latlon[1] for latlon in nearest_latlons if (latlon[0],) == lat_child.values]
                lon_children_by_values = {child.values: child for child in lat_child.children}
                lon_children_values = list(lon_children_by_values.keys())
                for lon_child_val in lon_children_values:
                    lon_child = lon_children_by_values[lon_child_val]
                    for value in lon_child.values:
                        if value not in possible_lons:
                            lon_child.remove_compressed_branch(value)
        return point_tags
