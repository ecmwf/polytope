# this is using soil moisture example with data from
# https://www.earthdata.nasa.gov/learn/find-data/near-real-time/hazards-and-disasters/floods

import xarray as xr

data = xr.open_dataset("./example_eo/data/soil_moisture.nc")
print(data)

# try to work instead with sentinel 1b data...
