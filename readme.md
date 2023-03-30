# Polytope

Polytope is a library for extracting complex data from datacubes. It provides an API for non-orthogonal access to data, where the stencil used to extract data from the datacube can be any arbitrary n-dimensional polygon (called a *polytope*). This can be used to efficiently extract complex features from a datacube, such as polygon regions or spatio-temporal paths.

Polytope is designed to extend different datacube backends.
* Xarray dataarrays
* FDB object stores (coming soon)

Polytope supports datacubes which have branching, non-uniform indexing, and even cyclic axes. If the datacube backend supports byte-addressability and efficient random access (either in-memory on direct from storage), *polytope* can be used to dramatically decrease overall IO load.

# Installation 

Install the polytope software with Python 3 (>=3.7) from GitHub directly with the command

    python3 -m pip install --upgrade git+https://github.com/ecmwf/polytope.git@master

or from Pypi with the command

    python3 -m pip install polytope

# Example

Here is a step-by-step example of how to use this software.

1. First, instantiate all necessary Polytope components. In particular, provide a datacube, an API and a slicer instance. 

In the following example, we first specify the data which will be in our Xarray datacube. Note that the data here comes from the GRIB file called "winds.grib".
<!-- -->
        import xarray as xr
        xr.open_dataset("winds.grib", engine="cfgrib")
We then choose an appropriate slicer component,
<!-- -->
        slicer = HullSlicer()
before building an appropriate mid-level API, with all the necessary information to run our software. 
<!-- -->
        options = {"longitude": {"Cyclic": [0, 360.0]}}

        API = Polytope(datacube=array, engine=slicer, options=options)
<!-- -->
Note that the API is the component which instantiates the Datacube component. We thus provide the additional datacube options, such as the cyclicity information of some axes in this step.

2. Second, instantiate 

<!-- # Requirements

Python >= 3.7 (for OrderedDict)
TODO: populate requirements.txt -->
