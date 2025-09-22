import time

import numpy as np
import xarray as xr

from polytope_feature.datacube.backends.xarray import XArrayDatacube
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box, Disk, Ellipsoid, Select


class Test:
    def setup_method(self):
        array = xr.open_dataset("../examples/data/temp_model_levels.grib", engine="cfgrib").t
        options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        for dim in array.dims:
            array = array.sortby(dim)
        self.array = array
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_scalability_2D(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [0, 0], [50, 360])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        # result.pprint()
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_v2(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [0, 0], [100, 360])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_v3(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [-50, 0], [100, 360])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_v4(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [-100, 0], [100, 360])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_v5(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [0, 0], [50, 180])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_v6(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [-100, -180], [100, 360])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_v7(self):
        time_start = time.time()
        print(time_start)
        box = Box(["latitude", "longitude"], [-100, -360], [100, 360])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step"], [0, 0, np.timedelta64(0, "s")], [50, 360, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D_v2(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step"], [0, 0, np.timedelta64(0, "s")], [90, 360, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D_v3(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step"], [0, 0, np.timedelta64(0, "s")], [100, 360, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D_v4(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step"], [0, 0, np.timedelta64(0, "s")], [50, 180, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_disk(self):
        time_start = time.time()
        print(time_start)
        box = Disk(["latitude", "longitude"], [0, 0], [25, 180])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        # result.pprint()
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_disk_v2(self):
        time_start = time.time()
        print(time_start)
        box = Disk(["latitude", "longitude"], [0, 0], [50, 180])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        # result.pprint()
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_2D_disk_v3(self):
        time_start = time.time()
        print(time_start)
        box = Disk(["latitude", "longitude"], [0, 0], [25, 90])
        request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
        result = self.API.retrieve(request)
        # result.pprint()
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D_disk(self):
        time_start = time.time()
        print(time_start)
        box = Ellipsoid(
            ["latitude", "longitude", "step"], [0, 0, np.timedelta64(0, "s")], [25, 180, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D_v3_bis(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step"], [-50, 0, np.timedelta64(0, "s")], [90, 360, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_3D_v4_bis(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step"], [-50, -180, np.timedelta64(0, "s")], [90, 360, np.timedelta64(3600, "s")]
        )
        request = Request(box, Select("hybrid", [1]))
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_4D(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step", "hybrid"],
            [0, 0, np.timedelta64(0, "s"), 0],
            [50, 360, np.timedelta64(3600, "s"), 2],
        )
        request = Request(box)
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_4D_v2(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step", "hybrid"],
            [0, 0, np.timedelta64(0, "s"), 0],
            [100, 360, np.timedelta64(3600, "s"), 2],
        )
        request = Request(box)
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_4D_v3(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step", "hybrid"],
            [0, 0, np.timedelta64(0, "s"), 0],
            [50, 360, np.timedelta64(3600, "s"), 2],
        )
        request = Request(box)
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_4D_v4(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step", "hybrid"],
            [0, 0, np.timedelta64(0, "s"), 0],
            [50, 180, np.timedelta64(3600, "s"), 2],
        )
        request = Request(box)
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    def test_scalability_4D_v5(self):
        time_start = time.time()
        print(time_start)
        box = Box(
            ["latitude", "longitude", "step", "hybrid"],
            [0, 0, np.timedelta64(0, "s"), 0],
            [25, 180, np.timedelta64(3600, "s"), 2],
        )
        print(time.time())  # test to see how long it takes to create a box...
        request = Request(box)
        result = self.API.retrieve(request)
        print(len(result.leaves))
        print(time.time() - time_start)

    # Also do examples with different shapes, for example disk could be easy, or maybe try polygon?
    # Also try with different grid sizes
    # Maybe try more 5D cubes?


# class Test():

#     def setup_method(self):
#         array = xr.open_dataset("temp_model_levels.grib", engine='cfgrib')
#         options = {"longitude" : {"Cyclic" : [0, 360.]}}
#         self.xarraydatacube = XArrayDatacube(array)
#         for dim in array.dims:
#             array = array.sortby(dim)
#         self.array = array
#         self.slicer = HullSlicer()
#         self.API = Polytope(datacube=array, engine=self.slicer, options=options)

#     def test_scalability_2D(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [0,0], [50,360])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         # result.pprint()
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_v2(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [0, 0], [100, 360])
#         request = Request(box, Select("step", [np.timedelta64(0, "ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_v3(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [-50,0], [100,360])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_v4(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [-100,0], [100,360])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_v5(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [0,0], [50,180])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_v6(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [-100,-180], [100,360])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_v7(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude"], [-100,-360], [100,360])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step"], [0,0, np.timedelta64(0, "s")],
#                   [50,360, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D_v2(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step"], [0,0, np.timedelta64(0, "s")],
#                   [90,360, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D_v3(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step"], [0,0, np.timedelta64(0, "s")],
#                   [100,360, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D_v4(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step"], [0,0, np.timedelta64(0, "s")],
#                   [50,180, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_disk(self):
#         time_start = time.time()
#         print(time_start)
#         box = Disk(["latitude", "longitude"], [0,0], [25,180])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         # result.pprint()
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_disk_v2(self):
#         time_start = time.time()
#         print(time_start)
#         box = Disk(["latitude", "longitude"], [0,0], [50,180])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         # result.pprint()
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_2D_disk_v3(self):
#         time_start = time.time()
#         print(time_start)
#         box = Disk(["latitude", "longitude"], [0,0], [25,90])
#         request = Request(box, Select("step", [np.timedelta64(0,"ns")]), Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         # result.pprint()
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D_disk(self):
#         time_start = time.time()
#         print(time_start)
#         box = Ellipsoid(["latitude", "longitude", "step"], [0,0, np.timedelta64(0, "s")],
#                         [25,180, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D_v3(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step"], [-50,0, np.timedelta64(0, "s")],
#                   [90,360, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_3D_v4(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step"], [-50,-180, np.timedelta64(0, "s")],
#                   [90,360, np.timedelta64(3600, "s")])
#         request = Request(box,  Select("hybrid", [1]))
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_4D(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step", "hybrid"], [0,0, np.timedelta64(0, "s"), 0],
#                   [50,360, np.timedelta64(3600, "s"), 2])
#         request = Request(box)
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_4D_v2(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step", "hybrid"], [0,0, np.timedelta64(0, "s"), 0],
#                   [100,360, np.timedelta64(3600, "s"), 2])
#         request = Request(box)
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_4D_v3(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step", "hybrid"], [0,0, np.timedelta64(0, "s"), 0],
#                   [50,360, np.timedelta64(3600, "s"), 2])
#         request = Request(box)
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_4D_v4(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step", "hybrid"], [0,0, np.timedelta64(0, "s"), 0],
#                   [50,180, np.timedelta64(3600, "s"), 2])
#         request = Request(box)
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)

#     def test_scalability_4D_v5(self):
#         time_start = time.time()
#         print(time_start)
#         box = Box(["latitude", "longitude", "step", "hybrid"], [0,0, np.timedelta64(0, "s"), 0],
#                   [25,180, np.timedelta64(3600, "s"), 2])
#         print(time.time()) # test to see how long it takes to create a box...
#         request = Request(box)
#         result = self.API.retrieve(request)
#         print(len(result.leaves))
#         print(time.time()-time_start)
