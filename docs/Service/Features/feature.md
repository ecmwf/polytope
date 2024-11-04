# User Guide for Polytope Feature Extraction on ECMWF Data

## Introduction

Polytope is a service which enables users to download "features" from entire datacubes of earth system data. The best way to access this data is via [earthkit-data](https://earthkit-data.readthedocs.io/en/latest/guide/sources.html#polytope).

Follow the links below to see how to request different types of features.

## Feature Documentation

- [Time Series](timeseries.md)
- [Vertical Profile](vertical_profile.md)
- [Polygon](polygon.md)
- [Bounding Box](boundingbox.md)
- [Trajectory](trajectory.md)

## Notes

Some important notes that hold for all features are that:

* The data has to exist in the fdb on the polytope server.
* No config is required to be passed when using this method, it is generated on the server side.
* Further details on the `from_source` method can be found here: https://earthkit-data.readthedocs.io/en/latest/guide/sources.html