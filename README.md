
<h3 align="center">
<img src="https://raw.githubusercontent.com/ecmwf/polytope/develop/docs/images/polytope_logo_new_animated_AdobeExpress_3.gif" width=60%>
</br>

</h3>

<p align="center">
<a href="https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity">
    <img src="https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity/incubating_badge.svg" alt="Project Maturity">
  </a>
<a href="https://github.com/ecmwf/codex/raw/refs/heads/main/ESEE"> <img src="https://github.com/ecmwf/codex/raw/refs/heads/main/ESEE/data_provision_badge.svg" alt="ESEE">
</p>

<p align="center">
  <a href="https://github.com/ecmwf/polytope/actions/workflows/downstream-ci.yml">
  <img src="https://github.com/ecmwf/polytope/actions/workflows/downstream-ci.yml/badge.svg" alt="ci">
</a>
  <a href="https://codecov.io/gh/ecmwf/polytope"><img src="https://codecov.io/gh/ecmwf/polytope/branch/develop/graph/badge.svg"></a>
  <a href="https://opensource.org/licenses/Apache-2.0"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg"></a>
  <a href="https://github.com/ecmwf/polytope/releases"><img src="https://img.shields.io/github/v/release/ecmwf/polytope?color=blue&label=Release&style=flat-square"></a>
  <a href='https://polytope.readthedocs.io/en/latest/?badge=latest'><img src='https://readthedocs.org/projects/polytope/badge/?version=latest' alt='Documentation Status' /></a>
</p>
<p align="center">
  <a href="#concept">Concept</a> •
  <a href="#installation">Installation</a> •
  <a href="#example">Example</a> •
  <a href="#testing">Testing</a> •
  <a href="https://polytope.readthedocs.io/en/latest/">Documentation</a>
</p>

Polytope is a library for extracting complex data from datacubes. It provides an API for non-orthogonal access to data, where the stencil used to extract data from the datacube can be any arbitrary *n*-dimensional polygon (called a *polytope*). This can be used to efficiently extract complex features from a datacube, such as polygon regions or spatio-temporal paths.

Polytope is designed to extend different datacube backends:
* XArray dataarrays
* FDB object stores (through the GribJump software)

Polytope supports datacubes which have branching, non-uniform indexing, and even cyclic axes. If the datacube backend supports byte-addressability and efficient random access (either in-memory or direct from storage), **Polytope** can be used to dramatically decrease overall I/O load.

> \[!IMPORTANT\]
> This software is **Incubating** and subject to ECMWF's guidelines on [Software Maturity](https://github.com/ecmwf/codex/raw/refs/heads/main/Project%20Maturity).

<!-- > [!WARNING]
> This project is BETA and will be experimental for the foreseeable future. Interfaces and functionality are likely to change, and the project itself may be scrapped. DO NOT use this software in any project/software that is operational. -->

## Concept 

Polytope is designed to enable extraction of arbitrary extraction of data from a datacube. Instead of the typical range-based bounding-box approach, Polytope can extract any shape of data from a datacube using a "polytope" (*n*-dimensional polygon) stencil.

<p align="center">
  <img src="https://raw.githubusercontent.com/ecmwf/polytope/develop//docs/Algorithm/Overview/images_overview/ecmwf_polytope.png" alt="Polytope Concept" width="450"/>
</p>

The Polytope algorithm can for example be used to extract:

- 2D cut-outs, such as country cut-outs, from a datacube
    <p align="center">
        <img src="https://raw.githubusercontent.com/ecmwf/polytope/develop/docs/images/greece.png" alt="Greece cut-out" width="250"/>
    </p>

- timeseries from a datacube
    <p align="center">
        <img src="https://raw.githubusercontent.com/ecmwf/polytope/develop/docs/images/timeseries.png" alt="Timeseries" width="350"/>
    </p>

- more complicated spatio-temporal paths, such as flight paths, from a datacube
    <p align="center">
        <img src="https://raw.githubusercontent.com/ecmwf/polytope/develop/docs/images/flight_path.png" alt="Flight path" width="350"/>
    </p>

- and many more high-dimensional shapes in arbitrary dimensions...

For more information about the Polytope algorithm, refer to our [paper](https://arxiv.org/abs/2306.11553). 
If this project is useful for your work, please consider citing this paper.

## Installation 

Install the polytope software with Python 3 (>=3.7) from GitHub directly with the command

    python3 -m pip install git+ssh://git@github.com/ecmwf/polytope.git@develop

or from PyPI with the command

    python3 -m pip install polytope-python

## Example

Here is a step-by-step example of how to use this software.

1. In this example, we first specify the data which will be in our Xarray datacube. Note that the data here comes from the GRIB file called "winds.grib", which is 3-dimensional with dimensions: step, latitude and longitude.
    ```Python
        import xarray as xr

        array = xr.open_dataset("winds.grib", engine="cfgrib")
    ```
   
    We then construct the Polytope object, passing in some additional metadata describing properties of the longitude axis.
    ```Python
        options = {"longitude": {"cyclic": [0, 360.0]}}

        from polytope_feature.polytope import Polytope

        p = Polytope(datacube=array, axis_options=options)
    ```

2. Next, we create a request shape to extract from the datacube.  
  In this example, we want to extract a simple 2D box in latitude and longitude at step 0. We thus create the two relevant shapes we need to build this 3-dimensional object,
    ```Python
        import numpy as np
        from polytope_feature.shapes import Box, Select

        box = Box(["latitude", "longitude"], [0, 0], [1, 1])
        step_point = Select("step", [np.timedelta64(0, "s")])
    ```

    which we then incorporate into a Polytope request.
    ```Python
        from polytope_feature.polytope import Request

        request = Request(box, step_point)
    ```

3. Finally, extract the request from the datacube. 
    ```Python
        result = p.retrieve(request)
    ```

    The result is stored as an IndexTree containing the retrieved data organised hierarchically with axis indices for each point.
    ```Python
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
    ```

## Testing

#### Additional Dependencies

The Polytope tests and examples require additional Python packages compared to the main Polytope algorithm.
The additional dependencies are provided in the requirements_test.txt and requirements_examples.txt files, which can respectively be found in the tests and examples folders.
Moreover, Polytope's tests and examples also require the installation of eccodes and GDAL.
It is possible to install both of these dependencies using either a package manager or manually.

## Contributing 

The main repository is hosted on GitHub; testing, bug reports and contributions are highly welcomed and appreciated. 
Please see the [Contributing](./CONTRIBUTING.rst) document for the best way to help. 

Main contributors: 

- Mathilde Leuridan - [ECMWF](https://www.ecmwf.int)
- James Hawkes - [ECMWF](https://www.ecmwf.int)
- Simon Smart - [ECMWF](www.ecmwf.int)
- Emanuele Danovaro - [ECMWF](www.ecmwf.int)
- Tiago Quintino - [ECMWF](www.ecmwf.int)

See also the [contributors](https://github.com/ecmwf/polytope/contributors) for a more complete list. 

## License 

```
Copyright 2021 European Centre for Medium-Range Weather Forecasts (ECMWF)

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at [http://www.apache.org/licenses/LICENSE-2.0](http://www.apache.org/licenses/LICENSE-2.0).

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

In applying this licence, ECMWF does not waive the privileges and immunities
granted to it by virtue of its status as an intergovernmental organisation nor
does it submit to any jurisdiction.
```

## Citing 

If this software is useful in your work, please consider citing our paper as 

> Leuridan, M., Hawkes, J., Smart, S., Danovaro, E., and Quintino, T., [“Polytope: An Algorithm for Efficient Feature Extraction on Hypercubes”](https://arxiv.org/abs/2306.11553), <i>arXiv e-prints</i>, 2023. doi:10.48550/arXiv.2306.11553.

Other papers include: 

> Leuridan, M., Bradley, C., Hawkes, J., Quintino, T., & Schultz, M. (2025, June). [Performance Analysis of an Efficient Algorithm for Feature Extraction from Large Scale Meteorological Data Stores.](https://dl.acm.org/doi/abs/10.1145/3732775.3733573) In Proceedings of the Platform for Advanced Scientific Computing Conference (pp. 1-9).

## Acknowledgements

Past and current funding and support for **Polytope** is listed in the adjoining [Acknowledgements](./ACKNOWLEDGEMENTS.rst).


