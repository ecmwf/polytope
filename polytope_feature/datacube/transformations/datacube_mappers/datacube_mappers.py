from copy import deepcopy

from ..datacube_transformations import DatacubeAxisTransformation

try:
    from polytope_feature.polytope_rs import (
        HealpixGridMapper,
    )
    from polytope_feature.polytope_rs import (
        LambertConformalGridMapper as RustLambertConformalGridMapper,
    )
    from polytope_feature.polytope_rs import (
        LocalRegularGridMapper,
        NestedHealpixGridMapper,
        OctahedralGridMapper,
        ReducedGaussianGridMapper,
        ReducedLatLonMapper,
        RegularGridMapper,
    )

    _RUST_AVAILABLE = True
except (ModuleNotFoundError, ImportError):
    _RUST_AVAILABLE = False


class DatacubeMapper(DatacubeAxisTransformation):
    # Needs to implements DatacubeAxisTransformation methods

    def __init__(self, name, mapper_options, datacube=None):
        self.transformation_options = mapper_options
        self.grid_type = mapper_options.type
        self.grid_resolution = mapper_options.resolution
        self.grid_axes = mapper_options.axes
        self.local_area = []
        self.md5_hash = None
        if mapper_options.md5_hash is not None:
            self.md5_hash = mapper_options.md5_hash
        if mapper_options.local is not None:
            self.local_area = mapper_options.local
        self._axis_reversed = None
        if mapper_options.axis_reversed is not None:
            self._axis_reversed = mapper_options.axis_reversed
        self.mapper_options = mapper_options
        self.old_axis = name
        self._final_transformation = self.generate_final_transformation()
        # Support both Python mapper objects (_mapped_axes) and Rust objects (mapped_axes).
        # For Rust irregular mappers that do not expose mapped_axes, fall back to grid_axes.
        for attr in ("_mapped_axes", "mapped_axes"):
            if hasattr(self._final_transformation, attr):
                self._final_mapped_axes = getattr(self._final_transformation, attr)
                break
        else:
            self._final_mapped_axes = self.grid_axes
        # Resolve axis_reversed from the mapper (Rust exposes it as `axis_reversed` dict,
        # Python uses `_axis_reversed`)
        _resolved = None
        for attr in ("_axis_reversed", "axis_reversed"):
            if hasattr(self._final_transformation, attr):
                _resolved = getattr(self._final_transformation, attr)
                break

        if isinstance(_resolved, dict):
            self._axis_reversed = _resolved
        elif hasattr(self._axis_reversed, "__getitem__"):
            pass  # already a dict-like from mapper_options
        else:
            # Default: first axis reversed, second axis not
            self._axis_reversed = {self._mapped_axes()[0]: True, self._mapped_axes()[1]: False}
        self._compressed_grid_axes = getattr(
            self._final_transformation,
            "compressed_grid_axes",
            [self._final_mapped_axes[1]],
        )
        self.merged_latlon = False
        self.md5_hash = getattr(self._final_transformation, "md5_hash", None)
        self.is_irregular = getattr(self._final_transformation, "is_irregular", False)

    @property
    def compressed_grid_axes(self):
        if self.merged_latlon:
            return []
        return self._compressed_grid_axes

    @compressed_grid_axes.setter
    def compressed_grid_axes(self, value):
        self._compressed_grid_axes = value

    def generate_final_transformation(self):
        constructor = _type_to_datacube_mapper_lookup[self.grid_type]
        if constructor is None:
            # icon: fall back to Python IrregularGridMapper
            from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.irregular import (
                IrregularGridMapper,
            )

            transformation = deepcopy(
                IrregularGridMapper(
                    self.old_axis,
                    self.grid_axes,
                    self.grid_resolution,
                    self.md5_hash,
                    self.local_area,
                    self._axis_reversed,
                    self.mapper_options,
                )
            )
            return transformation._final_irregular_transformation
        else:
            transformation = constructor(
                self.old_axis,
                self.grid_axes,
                self.grid_resolution,
                self.md5_hash,
                self.local_area,
                self._axis_reversed,
                self.mapper_options,
            )
            return transformation

    def blocked_axes(self):
        return []

    def unwanted_axes(self):
        return [self._final_mapped_axes[0]]

    def transformation_axes_final(self):
        final_axes = self._final_mapped_axes
        return final_axes

    # Needs to also implement its own methods

    def change_val_type(self, axis_name, values):
        # the new axis_vals created will be floats
        if self.merged_latlon:
            return [(0.0, 0.0)]
        return [0.0]

    def _mapped_axes(self):
        # NOTE: Each of the mapper method needs to call it's sub mapper method
        final_axes = self._final_mapped_axes
        return final_axes

    def _base_axis(self):
        pass

    def _resolution(self):
        pass

    def first_axis_vals(self):
        return self._final_transformation.first_axis_vals()

    def second_axis_vals(self, first_val):
        return self._final_transformation.second_axis_vals(first_val)

    def map_first_axis(self, lower, upper):
        return self._final_transformation.map_first_axis(lower, upper)

    def map_second_axis(self, first_val, lower, upper):
        return self._final_transformation.map_second_axis(first_val, lower, upper)

    def find_second_idx(self, first_val, second_val):
        return self._final_transformation.find_second_idx(first_val, second_val)

    def unmap_first_val_to_start_line_idx(self, first_val):
        return self._final_transformation.unmap_first_val_to_start_line_idx(first_val)

    def unmap(self, first_val, second_val, unmapped_idx=None):
        return self._final_transformation.unmap(first_val, second_val, unmapped_idx)

    def find_modified_indexes(self, indexes, path, datacube, axis):
        if axis.name == self._mapped_axes()[0]:
            return self.first_axis_vals()
        if axis.name == self._mapped_axes()[1]:
            first_val = path[self._mapped_axes()[0]]
            if not isinstance(first_val, tuple):
                first_val = (first_val,)
            return self.second_axis_vals(first_val)

    def unmap_path_key(self, key_value_path, leaf_path, unwanted_path, axis):
        values = key_value_path[axis.name]
        if axis.name == self._mapped_axes()[0]:
            if self.merged_latlon:
                lat, lon = values[0]
                unmapped_idx = leaf_path.get("index", None)
                if unmapped_idx is not None and len(unmapped_idx) > 0:
                    unmapped_idx = list(unmapped_idx)
                else:
                    unmapped_idx = self.unmap((lat, lon), None, unmapped_idx)
                key_value_path[self.old_axis] = unmapped_idx
                return (key_value_path, leaf_path, unwanted_path)
            unwanted_val = key_value_path[self._mapped_axes()[0]]
            unwanted_path[axis.name] = unwanted_val
        if axis.name == self._mapped_axes()[1]:
            if self.merged_latlon:
                return (key_value_path, leaf_path, unwanted_path)
            first_val = unwanted_path[self._mapped_axes()[0]]
            unmapped_idx = leaf_path.get("index", None)
            if unmapped_idx is not None and len(unmapped_idx) > 0:
                unmapped_idx = list(unmapped_idx)
            else:
                unmapped_idx = self.unmap(first_val, values)
            leaf_path.pop(self._mapped_axes()[0], None)
            key_value_path.pop(axis.name)
            key_value_path[self.old_axis] = unmapped_idx
        return (key_value_path, leaf_path, unwanted_path)

    def unmap_tree_node(self, node, unwanted_path):
        values = node.values
        if node.axis.name == self._mapped_axes()[0]:
            if self.merged_latlon:
                # In merged mode, values are (lat, lon) tuples; extract unmapped indexes directly.
                unmapped_idxs = []
                for val in values:
                    lat, lon = val
                    unmapped_idx = self.unmap((lat, lon), None)
                    unmapped_idxs.append(unmapped_idx)
                returned_node = node.hide_non_index_nodes(unmapped_idxs)
                return (returned_node, unwanted_path)
            unwanted_path[node.axis.name] = values
            returned_node = node
        if node.axis.name == self._mapped_axes()[1]:
            if self.merged_latlon:
                return (node, unwanted_path)
            first_vals = unwanted_path[self._mapped_axes()[0]]
            unmapped_idxs = []
            for first_val in first_vals:
                for val in values:
                    unmapped_idx = self.unmap([first_val], [val])
                    unmapped_idxs.append(unmapped_idx)
            returned_node = node.hide_non_index_nodes(unmapped_idxs)
        return (returned_node, unwanted_path)


def _build_lookup():
    """Build the mapper lookup dict. Uses Rust classes when available, else falls back
    to Python mapper classes loaded via import_module."""
    if _RUST_AVAILABLE:
        return {
            "octahedral": OctahedralGridMapper,
            "healpix": HealpixGridMapper,
            "regular": RegularGridMapper,
            "reduced_ll": ReducedLatLonMapper,
            "local_regular": LocalRegularGridMapper,
            "lambert_conformal": RustLambertConformalGridMapper,
            "unstructured": _rust_unstructured_mapper(),
            "healpix_nested": NestedHealpixGridMapper,
            "icon": None,  # Not implemented in Rust; use Python IrregularGridMapper
            "reduced_gaussian": ReducedGaussianGridMapper,
        }
    else:
        from importlib import import_module

        def _python_mapper(grid_type, class_name):
            mod = import_module("polytope_feature.datacube.transformations.datacube_mappers.mapper_types." + grid_type)
            return getattr(mod, class_name)

        return {
            "octahedral": _python_mapper("octahedral", "OctahedralGridMapper"),
            "healpix": _python_mapper("healpix", "HealpixGridMapper"),
            "regular": _python_mapper("regular", "RegularGridMapper"),
            "reduced_ll": _python_mapper("reduced_ll", "ReducedLatLonMapper"),
            "local_regular": _python_mapper("local_regular", "LocalRegularGridMapper"),
            "lambert_conformal": None,  # handled via IrregularGridMapper
            "unstructured": None,  # handled via IrregularGridMapper
            "healpix_nested": _python_mapper("healpix_nested", "NestedHealpixGridMapper"),
            "icon": None,  # Python IrregularGridMapper
            "reduced_gaussian": _python_mapper("reduced_gaussian", "ReducedGaussianGridMapper"),
        }


def _rust_unstructured_mapper():
    try:
        from polytope_feature.polytope_rs import UnstructuredGridMapper

        return UnstructuredGridMapper
    except (ModuleNotFoundError, ImportError):
        return None


_type_to_datacube_mapper_lookup = _build_lookup()
