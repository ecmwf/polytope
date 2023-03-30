# Polytope

Polytope is a library for extracting complex data from datacubes. It provides an API for non-orthogonal access to data, where the stencil used to extract data from the datacube can be any arbitrary n-dimensional polygon (called a *polytope*). This can be used to efficiently extract complex features from a datacube, such as polygon regions or spatio-temporal paths.

Polytope is designed to extend different datacube backends.
* Xarray dataarrays
* FDB object stores (coming soon)

Polytope supports datacubes which have branching, non-uniform indexing, and even cyclic axes. If the datacube backend supports byte-addressability and efficient random access (either in-memory on direct from storage), *polytope* can be used to dramatically decrease overall IO load.

# Installation 

Install the polytope software with Python 3 (>=3.7) and pip using either

    python3 -m pip install --upgrade git+https://github.com/ecmwf/polytope.git@master

or from Pypi with the command

    python3 -m pip install polytope

# Example

<!-- # Requirements

Python >= 3.7 (for OrderedDict)
TODO: populate requirements.txt -->
