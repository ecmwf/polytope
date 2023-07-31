import numpy as np
from earthkit import data

from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select

ds = data.from_source("file", "./examples/data/winds.grib")
array = ds.to_xarray()
array = array.isel(time=0).isel(surface=0).isel(number=0).u10

axis_options = {"longitude": {"Cyclic": [0, 360.0]}}

p = Polytope(datacube=array, axis_options=axis_options)

box = Box(["latitude", "longitude"], [0, 0], [1, 1])
step_point = Select("step", [np.timedelta64(0, "s")])

request = Request(
    box, step_point, Select("number", [0]), Select("surface", [0]), Select("time", ["2022-09-30T12:00:00"])
)

result = p.retrieve(request)

result.pprint()
