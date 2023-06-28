import math

from earthkit import data

from polytope.datacube.octahedral_xarray import XArrayDatacube
from polytope.datacube.datacube_axis import FloatAxis
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Select

ds = data.from_source("file", "./foo.grib")
latlon_array = ds.to_xarray().isel(step=0).isel(number=0).isel(surface=0).isel(time=0)
latlon_array = latlon_array.t2m

# print(latlon_array)


# # Going from an index in the latlon array to individual lat and lon numbers
# index = 44+28

# lat_j = math.floor(-3.5 + (math.sqrt(81+2*index)/2))
# lon_j = index - 2 * lat_j * lat_j - 14 * lat_j + 16

# # NOTE to get idx of lat and lon, need to substract 1 to start from 0 for lat

# lat_idx = lat_j - 1
# lon_idx = lon_j

# print(lat_idx)
# print(lon_idx)

latlon_xarray_datacube = XArrayDatacube(latlon_array)

# print(xarraydatacube.mappers)

# lat_axis = FloatAxis()
# lat_axis.name = "latitude"
# xarraydatacube.get_indices({}, lat_axis, 5, 10)

# subxarray = latlon_array.isel(values=20)
# value = subxarray.item()
# key = subxarray.name
# print((value, key))

slicer = HullSlicer()
API = Polytope(datacube=latlon_array, engine=slicer)

request = Request(Box(["latitude", "longitude"], [5, 5], [10, 10]))
result = API.retrieve(request)
result.pprint()
