"""Prototype: BulkGridTensorIndexNode retrieval and field-by-field streaming (get_iter) on XArrayDatacube.

Builds a tiny (2 x 4 point) regular lat/lon grid directly as the "values" dimension of an in-memory
DataArray (resolution=1: latitude lines [90, 0], longitude points [0, 90, 180, 270], flat index
first_idx * 4 + second_idx), with an extra "step" dimension so there is something to stream fields over.
A BulkGridTensorIndexNode is built by hand (no Polytope/HullSlicer involved) spanning both latitude rows,
to check retrieval and streaming independently of how such a node eventually gets constructed during
slicing.
"""

import numpy as np
import xarray as xr

from polytope_feature.datacube.tensor_index_tree import BulkGridTensorIndexNode
from polytope_feature.polytope import Polytope

OPTIONS = {
    "axis_config": [
        {
            "axis_name": "values",
            "transformations": [
                {
                    "name": "mapper",
                    "type": "regular",
                    "resolution": 1,
                    "axes": ["latitude", "longitude"],
                }
            ],
        },
    ],
    "compressed_axes_config": ["longitude", "latitude", "step"],
}

# flat index = first_idx * 4 + second_idx; lat lines [90, 0], lon points [0, 90, 180, 270]
POINTS = [(90.0, 0.0), (90.0, 90.0), (0.0, 180.0), (0.0, 270.0)]
INDEXES = [0, 1, 6, 7]


def _make_datacube(n_steps=2):
    n_points = 8
    data = np.arange(n_steps * n_points, dtype=np.float64).reshape(n_steps, n_points)
    array = xr.DataArray(
        data,
        dims=("step", "values"),
        coords={"step": np.arange(n_steps)},
    )
    api = Polytope(datacube=array, options=OPTIONS)
    return api.datacube, array


def _make_bulk_node(datacube):
    lat_ax = datacube._axes["latitude"]
    lon_ax = datacube._axes["longitude"]
    return (
        lat_ax,
        lon_ax,
        BulkGridTensorIndexNode(
            [lat_ax, lon_ax],
            [90.0, 0.0],
            None,
            INDEXES,
            row_lengths=[2, 2],
            coordinates=np.asarray(POINTS, dtype=np.float64),
        ),
    )


class TestXArrayBulkGridRetrieval:
    def test_get_fills_bulk_node_result(self):
        """XArrayDatacube.get() already handles BulkGridTensorIndexNode via the BulkMergedTensorIndexNode
        branch (it is a subclass): this just makes that explicit and checks the values are correct."""
        datacube, array = _make_datacube(n_steps=1)
        _, _, node = _make_bulk_node(datacube)

        datacube.get(node, context={}, leaf_path={"step": (0,)})

        key, values = node.result
        expected = array.isel(step=0).values[INDEXES]
        assert np.array_equal(np.squeeze(values), expected)

    def test_get_iter_yields_one_field(self):
        datacube, array = _make_datacube(n_steps=1)
        _, _, node = _make_bulk_node(datacube)

        items = list(datacube.get_iter(node, context={}))
        assert len(items) == 1
        field_path, leaf_values = items[0]
        assert field_path == {}
        [(yielded_node, values)] = leaf_values
        assert yielded_node is node
        assert np.array_equal(np.squeeze(values), array.isel(step=0).values[INDEXES])

    def test_get_iter_streams_one_field_per_step(self):
        """With a genuinely compressed non-spatial axis above it, get_iter yields one field at a time,
        in step order, each holding just that step's points -- matching FDBDatacube.get_iter's contract."""
        n_steps = 3
        datacube, array = _make_datacube(n_steps=n_steps)
        _, _, node = _make_bulk_node(datacube)

        items = list(
            datacube.get_iter(node, context={}, leaf_path={"step": tuple(range(n_steps))}, field_names=["step"])
        )

        assert len(items) == n_steps
        for i, (field_path, leaf_values) in enumerate(items):
            assert field_path == {"step": i}
            [(yielded_node, values)] = leaf_values
            assert yielded_node is node
            assert np.array_equal(values, array.isel(step=i).values[INDEXES])

    def test_get_iter_matches_get(self):
        """get_iter's fields concatenate (in order) to the same values get() fills onto the node."""
        n_steps = 3
        datacube, array = _make_datacube(n_steps=n_steps)
        _, _, node = _make_bulk_node(datacube)

        datacube.get(node, context={}, leaf_path={"step": tuple(range(n_steps))})
        _, eager_values = node.result

        datacube2, _ = _make_datacube(n_steps=n_steps)
        _, _, node2 = _make_bulk_node(datacube2)
        streamed = [
            values
            for _, [(_, values)] in datacube2.get_iter(
                node2, leaf_path={"step": tuple(range(n_steps))}, field_names=["step"]
            )
        ]

        assert eager_values.shape[0] == n_steps
        for i in range(n_steps):
            assert np.array_equal(eager_values[i], streamed[i])
