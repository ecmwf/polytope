# Polytope Feature Extraction

Polytope is a web service designed to provide efficient access to datacubes. Polytope's key feature is the ability to directly extract **features** from a datacube, as well as whole fields, without any intermediate copies.

Features currently includes time-series, vertical profiles, a custom polygon region, bounding box or spatio-temporal trajectory.

Extracting features directly offers two main advantages:

- Reduced I/O usage when requesting data from large datacubes, which means less data downloaded.

- Reduced post-processing needs for users after extraction, making the data more analysis-ready.

<div style="text-align:center">
<p style="float: middle; margin: 0 5px 0 0px;">
    <img src="../../images/polytope_feature.png" alt="Example Features" width="750"/>
</p>
</div>

## Polytope Feature Extraction vs Web MARS

Feature extraction differs from Web-MARS by allowing users to request specific features rather than only global fields. However, Polytope does also allow users to request global fields by simply omitting the `feature` keyword from the request. 

Both Polytope and Web-MARS are integrated into the earthkit ecosystem allowing users to request and retrieve data using either service. Earthkit tools for mapping, plotting, regridding, and transforming are available for working with both whole fields and specific features.

## Feature Extraction Client

The recommended client for Polytope Feature Extraction is earthkit-data. A guide on how to install earthkit-data can be found <a href="../Installation">here</a>, a quick start user guide is also provided <a href="../Quick_Start">here</a>. This allows users to quickly install earthkit-data and to begin making requests.

For more in-depth information about the various features see the following pages:

### <a href="../Features/feature">Features</a>
  - <a href="../Features/timeseries">Timeseries</a>
  - <a href="../Features/vertical_profile">Vertical Profile</a>
  - <a href="../Features/polygon">Polygon</a>
  - <a href="../Features/boundingbox">Bounding Box</a>
  - <a href="../Features/trajectory">Trajectory</a>
  - <a href="../Feature/circle">Circle</a>
  - <a href="../Feature/position">Position</a>

<!-- A design document on the general principles of how requests can be generated can also be found <a href="../Design_Doc">here</a>. -->

A set of example notebooks can also be found in the <a href="../Examples/examples">Examples</a> page along with some examples of integration with other earthkit libraries.

A <a href="../Data_Portfolio">Data Portfolio</a> containing information on what data we provide is also available.
