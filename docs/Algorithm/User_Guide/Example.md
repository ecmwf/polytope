# Example
Here is a step-by-step example of how to use the Polytope software.

1. In this example, we first specify the data which will be in our Xarray datacube. Note that the data here comes from the GRIB file called "winds.grib", which is 3-dimensional with dimensions: step, latitude and longitude.

        import xarray as xr

        array = xr.open_dataset("winds.grib", engine="cfgrib")
   
    We then construct the Polytope object, passing in some additional metadata describing properties of the longitude axis.

        options = {"longitude": {"Cyclic": [0, 360.0]}}

        from polytope.polytope import Polytope

        p = Polytope(datacube=array, options=options)

2. Next, we create a request shape to extract from the datacube.  
  In this example, we want to extract a simple 2D box in latitude and longitude at step 0. We thus create the two relevant shapes we need to build this 3-dimensional object,

        import numpy as np
        from polytope.shapes import Box, Select

        box = Box(["latitude", "longitude"], [0, 0], [1, 1])
        step_point = Select("step", [np.timedelta64(0, "s")])

    which we then incorporate into a Polytope request.

        from polytope.polytope import Request

        request = Request(box, step_point)

3. Finally, extract the request from the datacube. 

        result = p.retrieve(request)

    The result is stored as an IndexTree containing the retrieved data organised hierarchically with axis indices for each point.
    
        result.pprint()
        

        Output IndexTree: 

            ↳root=None
                ↳step=0 days 00:00:00
                        ↳latitude=0.0
                                ↳longitude=0.0
                                ↳longitude=1.0
                        ↳latitude=1.0
                                ↳longitude=0.0
                                ↳longitude=1.0