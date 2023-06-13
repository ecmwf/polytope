import numpy as np
import xarray as xr

from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select

array = xr.open_dataset("./examples/data/winds.grib", engine="cfgrib").u10

options = {"longitude": {"Cyclic": [0, 360.0]}}

p = Polytope(datacube=array, options=options)

box = Box(["latitude", "longitude"], [0, 0], [1, 1])
step_point = Select("step", [np.timedelta64(0, "s")])

request = Request(box, step_point)

result = p.retrieve(request)

result.pprint()
