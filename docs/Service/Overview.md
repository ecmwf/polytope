# Polytope Feature Extraction

Polytope is an open-source web service designed to provide efficient access to hypercubes of data in scientific analysis workflows and is able to federate access between hypercubes in distributed computing resources. It is designed to couple data-centric workflows operating across multiple platforms (HPC, cloud) and across multiple distributed sites.

Polytope feature extraction allows users instead of extracting global fields to only extract data of interest to them, whether this is a time-series, a vertical profile, or a custom region. This approach offers a number of different advantages:

- Reduce I/O usage when requesting data from large datacubes and

- Reduce post-processing needs for users after extraction.

## Polytope Feature Extraction vs Web-Mars

Feature Extraction differs from web-mars in the fact that it allows users to request specific features rather than only gloabl fields, as mentioned above this provides a number of benefits. Polytope also allows users to request global fields by simply omitting the `feature` keyword from the request. 

Feature extraction is also integrated into the Earthkit ecosystem allowing users to request and retireve data using Polytope and then immediately use it with other earthkit tools for mapping, plotting, regridding, and transforming.

## Feature Extraction Frontend

The recommended front-end for Polytope Feature Extraction is Earthkit-data. A guide on how to install earthkit-data can be found <a href="./Installation">here</a>, a quick start user guide is also provided <a href="./Quick_Start">here</a>. This allows users to quickly install Earthkit-data and to begin making requests.

For more in-depth information about the various features see the following pages:

- <a href="./Features">Features</a>
  - <a href="./Features/Timeseries">Timeseries</a>
  - <a href="./Features/Vertical_Profile">Vertical Profile</a>
  - <a href="./Features/Polygon">Polygon</a>
  - <a href="./Features/Bounding_Box">Bounding_Box</a>
  - <a href="./Features/Trajectory">Trajectory</a>

A design document on the general principles of how requests can be generated can also be found <a href="./Design_Doc">here</a>.

A set of example notebooks can also be found in the <a href="./Examples">Examples</a> page along with some examples of integration with other Earthkit libraries.