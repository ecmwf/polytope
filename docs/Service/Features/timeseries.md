# TimeSeries

## Basic Example

An example of a time-series requested via earthkit-data:

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
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "time_axis": "step",
        "range" : {
            "start" : 0,
            "end" : 360,
        }
        "axes" : ["latitude", "longitude"]
    },
    "format": "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```
The following will return a timeseries starting yesterday at 00Z with steps from `0` to `360` including all steps available in between, for the parameters `164/167/169` at the point given. This data will be returned for each ensemble number requested.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

## Required Fields

For a timeseries within the `feature` dictionary three fields are required

* `type`
* `points`
* `time_axis`

For a timeseries `type` must be `timeseries`.

`points` must be a nested list with a points containing a latitude and a longitude.

`time_axis` refers to the axis on which to generate the timeseries. In this case the timeseries is generated across `step` based on the inputted `range`. However if the data requested was a climate dataset the `time_axis` may be `datetime` denoting that the timeseries is generated across that axis.


## Optional Fields

`range` is an optional field within `feature`. It refers to the extent of the `time_axis` on which the timeseries will be generated. In the above case where:

```python
    "axes": "step",
    "range" : {
        "start" : 0,
        "end" : 360,
    }
```

A timeseries across `step` will start at step `0` and end at step `360` with all steps found in between being included. `range` can also contain `interval`.

```python
    "axes": "step",
    "range" : {
        "start" : 0,
        "end" : 360,
        "interval" : 2,
    }
```
In this case every second step will be returned if it exists.

As `range` is an optional field it can be left out, however there is not a default value. Instead the user has to include the timeseries `time_axis` in the main body of the request like below:

```python
request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step" : "0/to/360",
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "time_axis": "step",
    },
    "format": "covjson",
}
```

This is equivalent to the first request presented. 

At least one of `range` or `step` must be included in the request, but not both. In this case an error will be provided telling the user that `step` is overspecified.

Conversely at least one of `range` or `step` must be included.

`axes` can also be provided which defines the spatial `axes` on which the request is made. For example if the user provides points in the order `longitude`, `latitude` they can add `axes` : `["longitude", "latitude"]`.

## Note:

Previously the `axes` keyword was used for `time_axis`. We still allow this behavior to satisfy backwards compatibility with previous requests.
