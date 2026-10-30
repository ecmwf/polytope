from copy import copy, deepcopy
from itertools import product

import numpy as np
import xarray as xr

from ..tensor_index_tree import BulkMergedTensorIndexNode, TensorIndexTree
from .datacube import Datacube


class XArrayDatacube(Datacube):
    """Xarray arrays are labelled, axes can be defined as strings or integers (e.g. "time" or 0)."""

    def __init__(
        self,
        dataarray: xr.DataArray,
        axis_options=None,
        compressed_axes_options=[],
        context=None,
    ):
        super().__init__(
            axis_options,
            compressed_axes_options,
        )

        if axis_options is None:
            axis_options = {}
        self.axis_options = axis_options
        self.axis_counter = 0
        self._axes = None
        self.dataarray = dataarray

        for name, values in dataarray.coords.variables.items():
            options = None
            for opt in self.axis_options:
                if opt.axis_name == name:
                    options = opt
            if name in dataarray.dims:
                self._check_and_add_axes(options, name, values)
                self.treated_axes.append(name)
                self.complete_axes.append(name)
            else:
                if self.dataarray[name].dims == ():
                    self._check_and_add_axes(options, name, values)
                    self.treated_axes.append(name)
        for name in dataarray.dims:
            if name not in self.treated_axes:
                options = None
                for opt in self.axis_options:
                    if opt.axis_name == name:
                        options = opt
                val = dataarray[name].values[0]
                self._check_and_add_axes(options, name, val)
                self.treated_axes.append(name)
        # add other options to axis which were just created above like "lat" for the mapper transformations for eg
        for name in self._axes:
            if name not in self.treated_axes:
                options = None
                for opt in self.axis_options:
                    if opt.axis_name == name:
                        options = opt
                val = self._axes[name].type
                self._check_and_add_axes(options, name, val)

    def find_point_cloud(self):
        # find the point cloud of irregular grid if it exists
        if self.grid_transformation.is_irregular:
            return self.grid_transformation._final_transformation.grid_latlon_points()

    def get(self, requests, context=None, leaf_path=None, axis_counter=0):
        if leaf_path is None:
            leaf_path = {}
        if isinstance(requests, TensorIndexTree):
            if requests.axis.name == "root":
                for c in requests.children:
                    self.get(c, context, leaf_path, axis_counter + 1)
            else:
                key_value_path = {requests.axis.name: requests.values}
                ax = requests.axis
                key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(
                    key_value_path, leaf_path, self.unwanted_path
                )
                leaf_path.update(key_value_path)
                if len(requests.children) != 0:
                    # We are not a leaf and we loop over
                    for c in requests.children:
                        if axis_counter == self.axis_counter - 1:
                            leaf_path["index"] = c.indexes
                        self.get(c, context, leaf_path, axis_counter + 1)
                else:
                    if self.axis_counter != axis_counter:
                        requests.remove_branch()
                    else:
                        # We are at a leaf and need to assign value to it
                        subxarray = self._select(leaf_path)
                        requests.result = (subxarray.name, subxarray.values)
        else:
            # A bulk node (BulkMergedTensorIndexNode for an unstructured grid, or its subclass
            # BulkGridTensorIndexNode folding a structured grid's rows): both carry their selection as
            # (coordinates, indexes) arrays rather than tree layers, and are handled identically here --
            # a mapped axis pair's unmap_path_key collapses both onto the same flattened "values"
            # dimension regardless of which kind of bulk node supplied the canonical indexes.
            first_ax = requests.axes[0]
            second_ax = requests.axes[1]
            if isinstance(requests, BulkMergedTensorIndexNode):
                # All points of a bulk leaf share the path above it and carry their own indexes,
                # so unmap one representative point and select all indexes at once
                values = tuple(requests.coordinates[0])
                indexes = requests.indexes.tolist()
            else:
                values = requests.values
                indexes = requests.indexes
            key_value_path = {first_ax.name: values[0]}
            key_value_path, leaf_path, self.unwanted_path = first_ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            leaf_path["index"] = indexes
            key_value_path = {second_ax.name: values[1]}
            key_value_path, leaf_path, self.unwanted_path = second_ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            subxarray = self._select(leaf_path)
            requests.result = (subxarray.name, subxarray.values)

    def get_iter(self, requests, context=None, leaf_path=None, axis_counter=0, field_names=()):
        """Fetch ``requests`` field by field, yielding ``(field_path, leaf_values)`` instead of filling the tree.

        Mirrors :meth:`FDBDatacube.get_iter`'s contract so a caller can consume either backend's tree the
        same way: each item is ``(field_path, [(node, values)])``, where ``field_path`` is ``{axis_name:
        value}`` for every non-spatial ancestor axis holding more than one value (outermost axis first,
        the order the tree descends in), and ``values`` is the field's points as the spatial leaf or bulk
        node's own array, in its existing point order.  Nothing is written to ``requests.result``.

        Unlike gribjump, xarray has no per-field network boundary to amortise: ``.sel()`` already selects
        every compressed axis' whole set of values in one vectorised call, which is the efficient way to
        read an in-memory (or dask-backed) array.  So only one ``.sel()`` call is made per spatial
        sub-tree, exactly as :meth:`get` makes -- streaming here means slicing the *already computed*
        result one field at a time with cheap ``.isel()`` views, so the caller holds one field's array
        alive at a time instead of the whole sub-tree's fields at once.

        ``leaf_path``/``axis_counter``/``field_names`` mirror ``get``'s own ``leaf_path`` parameter: pass
        them to call this directly on a spatial sub-tree (eg. a bulk node) whose ancestor path was already
        resolved elsewhere, without walking a full tree down to it first.
        """
        if context is None:
            context = {}
        self.unwanted_path = {}
        if leaf_path is None:
            leaf_path = {}
        yield from self._get_iter(requests, leaf_path, axis_counter, list(field_names))

    def _get_iter(self, requests, leaf_path, axis_counter, field_names):
        if isinstance(requests, TensorIndexTree):
            if requests.axis.name == "root":
                for c in requests.children:
                    yield from self._get_iter(c, leaf_path, axis_counter + 1, field_names)
                return
            key_value_path = {requests.axis.name: requests.values}
            ax = requests.axis
            key_value_path, leaf_path, self.unwanted_path = ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            if len(requests.children) != 0:
                # A non-spatial ancestor axis: a field dimension to stream over once it holds >1 value.
                child_field_names = field_names
                if len(requests.values) > 1:
                    child_field_names = field_names + [requests.axis.name]
                for c in requests.children:
                    if axis_counter == self.axis_counter - 1:
                        leaf_path["index"] = c.indexes
                    yield from self._get_iter(c, leaf_path, axis_counter + 1, child_field_names)
                return
            if self.axis_counter != axis_counter:
                return
            yield from self._yield_fields(requests, leaf_path, field_names)
        else:
            first_ax = requests.axes[0]
            second_ax = requests.axes[1]
            if isinstance(requests, BulkMergedTensorIndexNode):
                values = tuple(requests.coordinates[0])
                indexes = requests.indexes.tolist()
            else:
                values = requests.values
                indexes = requests.indexes
            key_value_path = {first_ax.name: values[0]}
            key_value_path, leaf_path, self.unwanted_path = first_ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            leaf_path["index"] = indexes
            key_value_path = {second_ax.name: values[1]}
            key_value_path, leaf_path, self.unwanted_path = second_ax.unmap_path_key(
                key_value_path, leaf_path, self.unwanted_path
            )
            leaf_path.update(key_value_path)
            yield from self._yield_fields(requests, leaf_path, field_names)

    def _yield_fields(self, node, leaf_path, field_names):
        """Select ``leaf_path``'s spatial sub-tree once, then yield it one field combination at a time."""
        subxarray = self._select(leaf_path)
        present = [name for name in field_names if name in subxarray.dims and subxarray.sizes[name] > 1]
        if not present:
            yield {}, [(node, subxarray.values)]
            return
        coord_values = {name: subxarray[name].values for name in present}
        for combo in product(*(range(subxarray.sizes[name]) for name in present)):
            selection = dict(zip(present, combo))
            field_path = {name: coord_values[name][idx] for name, idx in selection.items()}
            yield field_path, [(node, subxarray.isel(selection).values)]

    def _select(self, leaf_path):
        """One ``.sel()`` against the whole array for a fully-built path (every ancestor axis resolved)."""
        leaf_path_copy = deepcopy(leaf_path)
        unmapped_path = {}
        self.refit_path(leaf_path_copy, unmapped_path, leaf_path)
        for key in leaf_path_copy:
            if isinstance(leaf_path_copy[key], tuple):
                leaf_path_copy[key] = list(leaf_path_copy[key])
        for key in unmapped_path:
            if isinstance(unmapped_path[key], tuple):
                unmapped_path[key] = list(unmapped_path[key])
        subxarray = self.dataarray.sel(leaf_path_copy, method="nearest")
        subxarray = subxarray.sel(unmapped_path)
        return subxarray

    def datacube_natural_indexes(self, axis, subarray):
        if axis.name in self.complete_axes:
            indexes = next(iter(subarray.xindexes.values())).to_pandas_index()
        else:
            if subarray[axis.name].values.ndim == 0:
                # NOTE how we handle the two special datetime and timedelta cases to conform with numpy arrays
                if np.issubdtype(subarray[axis.name].values.dtype, np.datetime64):
                    indexes = [subarray[axis.name].astype("datetime64[us]").values]
                elif np.issubdtype(subarray[axis.name].values.dtype, np.timedelta64):
                    indexes = [subarray[axis.name].astype("timedelta64[us]").values]
                else:
                    indexes = [subarray[axis.name].values.tolist()]
            else:
                indexes = subarray[axis.name].values
        return indexes

    def refit_path(self, path_copy, unmapped_path, path):
        for key in path.keys():
            if key not in self.dataarray.dims:
                path_copy.pop(key)
            elif key not in self.dataarray.coords.dtypes:
                unmapped_path.update({key: path[key]})
                path_copy.pop(key, None)
            for key in self.dataarray.coords.dtypes:
                key_dtype = self.dataarray.coords.dtypes[key]
                if key_dtype.type is np.str_ and key in path.keys():
                    unmapped_path.update({key: path[key]})
                    path_copy.pop(key, None)

    def select(self, path, unmapped_path):
        path_copy = copy(path)
        for key in path_copy:
            key_value = path_copy[key][0]
            path_copy[key] = key_value
        for key in unmapped_path:
            key_value = unmapped_path[key][0]
            unmapped_path[key] = key_value
        path_second_copy = deepcopy(path_copy)
        self.refit_path(path_second_copy, unmapped_path, path_copy)
        subarray = self.dataarray.sel(path_second_copy, method="nearest")
        subarray = subarray.sel(unmapped_path)
        return subarray

    def ax_vals(self, name):
        treated_axes = []
        for _name, values in self.dataarray.coords.variables.items():
            treated_axes.append(_name)
            if _name == name:
                return values.values
        for _name in self.dataarray.dims:
            if _name not in treated_axes:
                if _name == name:
                    return self.dataarray[name].values[0]
