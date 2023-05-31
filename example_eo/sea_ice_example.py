import xarray as xr
import matplotlib.pyplot as plt
import geopandas as gpd
import numpy as np

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Path, Select


# data from https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030/download
data = xr.open_dataset('./example_eo/data/sea_ice_data.nc')
print(data)

# create a polytope polyline object to extract
# or take shapefile from https://geodata.lib.utexas.edu/catalog/stanford-wz014rh6670

initial_shape = Box(["x", "y"], [0, 0], [2, 2])

# extract this shape from the sea ice datacube
# first create the sea ice datacube

xarraydatacube = XArrayDatacube(data)
array = data
slicer = HullSlicer()
API = Polytope(datacube=array, engine=slicer)

