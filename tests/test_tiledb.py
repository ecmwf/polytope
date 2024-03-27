import os
import shutil

import numpy as np
import pytest
import tiledb
import xarray as xr

from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box


class TestTileDB:

    def setup_method(self):
        cfg = tiledb.Ctx().config()
        cfg.update({'py.init_buffer_bytes': 1024**2 * 50})
        tiledb.default_ctx(cfg)

        # Create a TileDB object

        array_dense_1 = os.path.expanduser("~/array_dense_1")
        if os.path.exists(array_dense_1):
            shutil.rmtree(array_dense_1)

        d1 = tiledb.Dim(name="d1", domain=(0, 99), tile=2, dtype=np.int32)
        d2 = tiledb.Dim(name="d2", domain=(0, 99), tile=2, dtype=np.int32)

        # Create a domain using the two dimensions
        dom1 = tiledb.Domain(d1, d2)

        # Create an attribute
        a = tiledb.Attr(name="a", dtype=np.int32)

        # Create the array schema, setting `sparse=False` to indicate a dense array
        schema1 = tiledb.ArraySchema(domain=dom1, sparse=False, attrs=[a])

        # Create the array on disk (it will initially be empty)
        tiledb.Array.create(array_dense_1, schema1)

        data = np.random.randint(1, 100, (100, 100))

        A = tiledb.open(array_dense_1, 'w')

        A[:] = data

        xr_array = xr.open_dataset(array_dense_1, engine="tiledb")

        # Extract using Polytope

        slicer = HullSlicer()
        self.poly_API = Polytope(datacube=xr_array.a, engine=slicer)

    @pytest.mark.skip(reason="TileDB dependency")
    def test_tiledb(self):

        box1 = Box(["d1", "d2"], [3, 10], [6, 11])
        request = Request(box1)
        result = self.poly_API.retrieve(request)
        assert len(result.leaves) == 8
