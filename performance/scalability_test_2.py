import numpy as np
import xarray as xr
import time

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.shapes import *
from polytope.polytope import Request, Polytope



class Test():

    def setup_method(self):
        array = xr.open_dataset("temp_model_levels.grib", engine='cfgrib')
        options= {"longitude":{"Cyclic":[0,360.]}}
        self.xarraydatacube = XArrayDatacube(array)
        for dim in array.dims:
            array = array.sortby(dim)
        self.array = array 
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)


    # here we will see how long it takes to run on unions of smaller requests
    # def test_scalability_2D(self):
    #     union = Box(["latitude", "longitude"], [0,0], [5,36])
    #     for i in range(9):
    #         box = Box(["latitude", "longitude"], [5*(i+1),0], [5*(i+2),36])
    #         union = Union(["latitude", "longitude"], union, box)
    #     for j in range(9):
    #         box = Box(["latitude", "longitude"], [0,36*(j+1)], [5,36*(j+2)])
    #         union = Union(["latitude", "longitude"], union, box)
    #     for i in range(9):
    #         for j in range(9):
    #             box = Box(["latitude", "longitude"], [5*(i+1),36*(j+1)], [5*(i+2),36*(j+2)])
    #             union = Union(["latitude", "longitude"], union, box)
    #     time_start = time.time()
    #     print(time_start)
    #     request = Request(union, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
    #     result = self.API.retrieve(request)
    #     # result.pprint()
    #     print(len(result.leaves))
    #     print(time.time()-time_start)

    # def test_scalability_2D_v2(self):
    #     union = Box(["latitude", "longitude"], [0,0], [10,36])
    #     for i in range(9):
    #         box = Box(["latitude", "longitude"], [10*(i+1),0], [10*(i+2),36])
    #         union = Union(["latitude", "longitude"], union, box)
    #     for j in range(9):
    #         box = Box(["latitude", "longitude"], [0,36*(j+1)], [10,36*(j+2)])
    #         union = Union(["latitude", "longitude"], union, box)
    #     for i in range(9):
    #         for j in range(9):
    #             box = Box(["latitude", "longitude"], [10*(i+1),36*(j+1)], [10*(i+2),36*(j+2)])
    #             union = Union(["latitude", "longitude"], union, box)
    #     time_start = time.time()
    #     print(time_start)
    #     request = Request(union, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
    #     result = self.API.retrieve(request)
    #     print(len(result.leaves))
    #     print(time.time()-time_start)

    def test_scalability_2D_v3(self):
        union = Box(["latitude", "longitude"], [0-50,0], [15-50,36])
        for i in range(9):
            box = Box(["latitude", "longitude"], [15*(i+1)-50,0], [15*(i+2)-50,36])
            union = Union(["latitude", "longitude"], union, box)
        for j in range(9):
            box = Box(["latitude", "longitude"], [0-50,36*(j+1)], [15-50,36*(j+2)])
            union = Union(["latitude", "longitude"], union, box)
        for i in range(9):
            for j in range(9):
                box = Box(["latitude", "longitude"], [15*(i+1)-50,36*(j+1)], [15*(i+2)-50,36*(j+2)])
                union = Union(["latitude", "longitude"], union, box)
        time_start = time.time()
        print(time_start)
        request = Request(union, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        # result.pprint()
        print(len(result.leaves))
        print(time.time()-time_start)

    def test_scalability_2D_v4(self):
        union = Box(["latitude", "longitude"], [0-100,0], [20-100,36])
        for i in range(9):
            box = Box(["latitude", "longitude"], [20*(i+1)-100,0], [20*(i+2)-100,36])
            union = Union(["latitude", "longitude"], union, box)
        for j in range(9):
            box = Box(["latitude", "longitude"], [0-100,36*(j+1)], [20-100,36*(j+2)])
            union = Union(["latitude", "longitude"], union, box)
        for i in range(9):
            for j in range(9):
                box = Box(["latitude", "longitude"], [20*(i+1)-100,36*(j+1)], [20*(i+2)-100,36*(j+2)])
                union = Union(["latitude", "longitude"], union, box)
        time_start = time.time()
        print(time_start)
        request = Request(union, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time()-time_start)

