# Full Field Extraction

## Introduction

Polytope allows users to download full field global data from a number of datasets such as the DestinE Climate Digital Twin, Extremes Digital Twin, and On-Demand Digital Twin. The best way to access this data is via [earthkit-data](https://earthkit-data.readthedocs.io/en/latest/guide/sources.html#polytope).

## Datasets available

Full field requests return GRIB data. They use the same keys as [MARS](https://confluence.ecmwf.int/display/UDOC/MARS+user+documentation), a user can make a request specified by these keys and data will be returned by the Polytope service. 

For full field extraction the Polytope Service only supports the following:

* ECMWF Operational Data from the last two days [Further Details](https://apps.ecmwf.int/mars-catalogue/)
* DestinE Climate Digital Twin [Further Details](https://confluence.ecmwf.int/display/DDCZArchive/Climate+DT+overview)
* DestinE Extremes Digital Twin [Further Details](https://confluence.ecmwf.int/display/DDCZArchive/Extremes+DT+overview)
* DestinE On-Demand Extremes Digital Twin
* ECMWF opendata for ai datasets [Further Details](https://confluence.ecmwf.int/display/DAC/ECMWF+open+data%3A+real-time+forecasts+from+IFS+and+AIFS#ECMWFopendata:realtimeforecastsfromIFSandAIFS-IndexFilesIndexfiles)

The following Catalogue can also be used to see what data is available and to generate requests for DestinE data: [https://catalogue.lumi.apps.dte.destination-earth.eu/](https://catalogue.lumi.apps.dte.destination-earth.eu/).

## Examples

An example of pulling operational full field data via Polytope.

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,  # Note: date must be within the last two days 
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step": "0",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

This request pulls three parameters from yesterdays forecast for all 50 ensemble members for step 0.

The following are other examples of full field extraction on other datasets.

  - <a href="./Examples/operational_example.ipynb">Operational</a>
  - <a href="./Examples/climate_dt_example.ipynb">Climate DT</a>
  - <a href="./Examples/extremes_dt_example.ipynb">Extremes DT</a>
  - <a href="./Examples/on-demand_dt_example.ipynb">On Demand DT</a>
  - <a href="./Examples/opendata_example.ipynb">Open Data</a>


More examples of DestinE data via Polytope can be found in the following [examples repo](https://github.com/destination-earth-digital-twins/polytope-examples/tree/main)


## Post Processing

Some server side post processing of the data before retrieval is available via Polytope. The following keys can be added to the requests.

### Grid

The grid keyword can be used to interpolate from one grid to another on the server side.

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,  # Note: date must be within the last two days 
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step": "0",
    "grid" : "0.25/0.25",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

In the above example we interpolate from the native grid to an `0.25/0.25` degree grid.

Further details about what girds are available to interpolate from and to can be found here: [grid keyword](https://confluence.ecmwf.int/pages/viewpage.action?pageId=123799065).

### Interpolation

An additional keyword when using `grid` is `interpolation`. Using this key one can define the interpolation method used.

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,  # Note: date must be within the last two days 
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step": "0",
    "grid" : "0.25/0.25",
    "interpolation" : "linear",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

The default interpolation is `linear`. The following options are available:

* linear
* bilinear
* nearest neighbour
* nearest lsm
* grid-box-average
* average

Further information on interpolation options can be found here: [interpolation keys](https://confluence.ecmwf.int/pages/viewpage.action?pageId=153389795).

### Area

A user can also request an area subselection of the data using the `area` keyword as follows.

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,  # Note: date must be within the last two days 
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step": "0",
    "area": "75/-15/30/42.5"
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

In this case only a subselection of Europe will be returned. The area coordinates are in the form `North/West/South/East`.

Further information on the `area` keyword can be found here: [area keyword](https://confluence.ecmwf.int/pages/viewpage.action?pageId=151520973).

## Notes

Some important notes that hold for all features are that:

* The data has to exist in the fdb on the polytope server.
* Further details on the `from_source` method can be found here: [https://earthkit-data.readthedocs.io/en/latest/guide/sources.html](https://earthkit-data.readthedocs.io/en/latest/guide/sources.html)