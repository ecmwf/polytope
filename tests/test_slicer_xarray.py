import xarray as xr
import numpy as np
import pandas as pd

from polytope.engine.hullslicer import HullSlicer
from polytope.shapes import *
from polytope.polytope import Request, Polytope

class TestXarraySlicing():

    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        dims = np.random.randn(3, 6, 129)
        array = xr.Dataset(
            data_vars=dict(param=(["date", "step", "level"], dims)),
            coords={
                "date": pd.date_range("2000-01-01", "2000-01-03", 3),
                "step": [0, 3, 6, 9, 12, 15],
                "level": range(1,130)
            }
        )

        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_2D_box(self):

        request = Request(
            Box(["step", "level"], [3,10], [6,11]),
            Select("date", ["2000-01-01"])  
        )
        result = self.API.retrieve(request)
        result.pprint()

    def test_2D_box_with_date_range(self):
        request = Request(
            Box(["step", "level"], [3,10], [6,11]),
            # TODO: conversion from numpy to Point class should allow dropping the pd.Timestamp, it should convert to correct type
            Span("date", lower=pd.Timestamp("2000-01-01"), upper=pd.Timestamp("2000-01-05"))
        )
        result = self.API.retrieve(request)
        result.pprint()

    def test_3D_box_with_date(self):

        request = Request(
            Box(["step", "level", "date"], [3,10, pd.Timestamp("2000-01-01")], [6,11, pd.Timestamp("2000-01-01")]),
        )
        result = self.API.retrieve(request)
        result.pprint()


        