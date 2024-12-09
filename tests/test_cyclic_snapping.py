import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Select


class TestSlicing3DXarrayDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        array = xr.DataArray(
            [0, 1, 2],
            dims=("long"),
            coords={
                "long": [0, 0.5, 1.0],
            },
        )

        options = {
            "axis_config": [{"axis_name": "long", "transformations": [{"name": "cyclic", "range": [0, 1.0]}]}],
            "compressed_axes_config": ["long"],
        }
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    # Testing different shapes

    def test_cyclic_float_axis_across_seam(self):
        request = Request(Select("long", [-0.2], method="surrounding"))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        assert result.leaves[0].flatten()["long"] == (0.0, 0.5)
        assert result.leaves[0].result[0] is None
        assert result.leaves[0].result[1][0] == 0
        assert result.leaves[0].result[1][1] == 1
