# Example
Here is a step-by-step example of how to use the Polytope software.

1. First, instantiate all necessary Polytope components. In particular, provide a datacube, an API and a slicer instance.  
 In this example, we first specify the data which will be in our Xarray datacube. Note that the data here comes from the GRIB file called ["winds.grib"](https://github.com/ecmwf/polytope/blob/develop/examples/data/winds.grib), which is 3-dimensional with dimensions: step, latitude and longitude.

        import xarray as xr

        array = xr.open_dataset("winds.grib", engine="cfgrib")
    We then choose an appropriate slicer component,

        from polytope.engine.hullslicer import HullSlicer

        slicer = HullSlicer()
    before building an appropriate mid-level API, with all the necessary information to run our software. 

        options = {"longitude": {"Cyclic": [0, 360.0]}}

        from polytope.polytope import Polytope

        API = Polytope(datacube=array, engine=slicer, options=options)
    Note that the API is the component which instantiates the Datacube component. We thus provide the additional datacube options, such as the cyclicity information of some axes in this step.

2. Second, create a request shape to extract from the datacube.  
  In this example, we want to extract a simple 2D box in latitude and longitude at step 0. We thus create the two relevant shapes we need to build this 3-dimensional object,

        from polytope.shapes import Box, Select

        box = Box(["latitude", "longitude"], [0,0], [10,10])
        step_point = Select("step", [np.timedelta64(0, "s")])

    which we then incorporate into a Polytope request.

        from polytope.polytope import Request

        request = Request(box, step_point)

3. Third, using the selected API, extract the request from the datacube. 

        result = API.retrieve(request)

    Note that the result is stored as a request tree containing the retrieved axis indices as nodes.