# Polytope

Polytope is a library for extracting complex data from datacubes. It provides an API for non-orthogonal access to data, where the stencil used to extract data from the datacube can be any arbitrary n-dimensional polygon (called a *polytope*). This can be used to efficiently extract complex features from a datacube, such as polygon regions or spatio-temporal paths.

Polytope is designed to extend different datacube backends.
* Xarray dataarrays
* FDB object stores (coming soon)

Polytope supports datacubes which have branching, non-uniform indexing, and even cyclic axes. If the datacube backend supports byte-addressability and efficient random access (either in-memory or direct from storage), *polytope* can be used to dramatically decrease overall I/O load.


| :warning: This project is BETA and will be experimental for the foreseeable future. Interfaces and functionality are likely to change. DO NOT use this software in any project/software that is operational. |
|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|

The broad concept behind the Polytope algorithm is summarised in the figure below. 
    <div style="text-align:center">
    <p style="float: middle; margin: 0 5px 0 0px;">
        <img src="./docs/Overview/images_overview/ecmwf_polytope.png" alt="Polytope Concept" width="450"/>
    </p>
    </div>

## Installation 

Install the polytope software with Python 3 (>=3.7) from GitHub directly with the command

    python3 -m pip install --upgrade git+https://github.com/ecmwf/polytope.git@master

or from Pypi with the command

    python3 -m pip install polytope

## Example

Here is a step-by-step example of how to use this software.

1. First, instantiate all necessary Polytope components. In particular, provide a datacube, an API and a slicer instance.  
 In this example, we first specify the data which will be in our Xarray datacube. Note that the data here comes from the GRIB file called "winds.grib", which is 3-dimensional with dimensions: step, latitude and longitude.

        import xarray as xr

        array = xr.open_dataset("winds.grib", engine="cfgrib")
   
    We then construct the Polytope object, passing in some additional metadata describing properties of the longitude axis.

        options = {"longitude": {"Cyclic": [0, 360.0]}}

        from polytope.polytope import Polytope

        p = Polytope(datacube=array, options=options)

2. Second, create a request shape to extract from the datacube.  
  In this example, we want to extract a simple 2D box in latitude and longitude at step 0. We thus create the two relevant shapes we need to build this 3-dimensional object,

        from polytope.shapes import Box, Select

        box = Box(["latitude", "longitude"], [0,0], [10,10])
        step_point = Select("step", [np.timedelta64(0, "s")])

    which we then incorporate into a Polytope request.

        from polytope.polytope import Request

        request = Request(box, step_point)

3. Finally, extract the request from the datacube. 

        result = p.retrieve(request)

    The result is stored as an IndexTree containing the retrieved data organised hierarchically with axis indices for each point.
    
        print(result)
        
        > 




<!-- # Requirements

Python >= 3.7 (for OrderedDict)
TODO: populate requirements.txt -->

## Testing

#### Git Large File Storage

Polytope uses Git Large File Storage (LFS) to store large test data files. 
Before cloning Polytope, it is thus necessary to install Git LFS, by following instructions provided [here](https://docs.github.com/en/repositories/working-with-files/managing-large-files/installing-git-large-file-storage) for example.

#### Extra Dependencies

The Polytope tests require the installation of eccodes and GDAL.
It is possible to install both of these dependencies using either a package manager or manually.
