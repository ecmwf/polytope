import numpy as np
import pytest
import xarray as xr

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Select, Span


class TestFloatType:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using float type
        array = xr.DataArray(
            np.random.randn(100, 101, 200),
            dims=("lat", "long", "alt"),
            coords={
                "lat": np.arange(0.0, 10.0, 0.1),
                "long": np.arange(4.09999, 4.1 + 0.0000001, 0.0000001),
                "alt": np.arange(0.0, 20.0, 0.1),
            },
        )
        self.slicer = HullSlicer()
        options = {"compressed_axes_config": ["lat", "long", "alt"]}
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slicing_span(self):
        request = Request(Span("lat", 4.1, 4.3), Select("long", [4.1]), Select("alt", [4.1]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1
        path = result.leaves[0].flatten()
        assert path["lat"] == (4.1, 4.2, 4.3)

    def test_slicing_point(self):
        request = Request(Select("lat", [4.1]), Select("long", [4.1]), Select("alt", [4.1]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1 and not result.leaves[0].is_root()

    @pytest.mark.skip(reason="Points too close, need exact arithmetic")
    def test_slicing_very_close_point(self):
        request = Request(Select("lat", [4.1]), Select("long", [4.0999919, 4.1]), Select("alt", [4.1]))
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1

    def test_slicing_points_higher_precision(self):
        request = Request(Select("lat", [4.12]), Select("long", [4.1]), Select("alt", [4.1]))
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].is_root()

    def test_slicing_points_empty_span_higher_precision(self):
        request = Request(Span("lat", 4.11, 4.12), Select("long", [4.1]), Select("alt", [4.1]))
        result = self.API.retrieve(request)
        assert result.leaves[0].is_root()

    def test_slicing_points_span_higher_precision(self):
        request = Request(Span("lat", 4.09, 4.12), Select("long", [4.1]), Select("alt", [4.1]))
        result = self.API.retrieve(request)
        assert not result.leaves[0].is_root() and len(result.leaves) == 1
