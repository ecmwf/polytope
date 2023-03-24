import xarray as xr
import numpy as np
import pytest
from decimal import *

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.shapes import *
from polytope.polytope import Request, Polytope

class TestFloatType():

    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using float type
        dims = np.random.randn(100, 101, 200)
        array = xr.Dataset(
            data_vars=dict(param=(["lat", "long", "alt"], dims)),
            coords={
                "lat": np.arange(0., 10., 0.1),
                "long": np.arange(4.09999, 4.1+0.0000001, 0.0000001),
                "alt": np.arange(0., 20., 0.1)
            }
        )

        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_slicing_span(self):
        # TODO: some problems with floating point values and values inside the datacube being slightly off.
        # This has been fixed by introducing tolerances, but could be better handled using exact arithmetic.
        
        request = Request(
            Span("lat", 4.1,4.3),
            Select("long",[4.1]),
            Select("alt",[4.1])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 3

    def test_slicing_point(self):
    
        request = Request(
            Select("lat", [4.1]),
            Select("long",[4.1]),
            Select("alt",[4.1])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1 and result.leaves[0].is_root() == False


    @pytest.mark.skip(reason="Points too close, need exact arithmetic")
    def test_slicing_very_close_point(self):
        
        request = Request(
            Select("lat", [4.1]),
            Select("long",[4.0999919,4.1]),
            Select("alt",[4.1])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert len(result.leaves) == 1

    def test_slicing_points_higher_precision(self):
        
        request = Request(
            Select("lat", [4.12]),
            Select("long",[4.1]),
            Select("alt",[4.1])
        )
        result = self.API.retrieve(request)
        result.pprint()
        assert result.leaves[0].is_root()

    def test_slicing_points_empty_span_higher_precision(self):
        
        request = Request(
            Span("lat", 4.11, 4.12),
            Select("long",[4.1]),
            Select("alt",[4.1])
        )
        result = self.API.retrieve(request)
        assert result.leaves[0].is_root()

    def test_slicing_points_span_higher_precision(self):
        
        request = Request(
            Span("lat", 4.09, 4.12),
            Select("long",[4.1]),
            Select("alt",[4.1])
        )
        result = self.API.retrieve(request)
        assert result.leaves[0].is_root() == False and len(result.leaves) == 1