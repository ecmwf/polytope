# Vertical Profile

## Basic Example
<!-- 
### Polytope-mars

A basic example of requesting a vertical profile using polytope-mars:

```python
from polytope_mars.api import PolytopeMars

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20241006",
    "time" : "0000",
    "levtype" : "pl",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step" : "0",
    "feature" : {
        "type" : "verticalprofile",
        "points": [[-9.10, 38.78]],
        "axes": "levelist",
        "range" : {
            "start" : 0,
            "end" : 1000,
        }
    },
    "format": "covjson",
}

result = PolytopeMars().extract(request)
```

The following will return a vertical profile on `2024-10-06 00:00:00` with levels from `0` to `1000` including all levels available in between, for the parameters `164/167/169` at the point given. This data will be returned for each ensemble number requested.

Notes: 
* The data has to exist in the data source pointed to in the config.
* No config is provided via the PolytopeMars interface so a config will be loaded from the default locations. The config can also be passed directly via the interface.

### Earthkit-data -->

An example vertical profile requested via earthkit-data:

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20241006",
    "time" : "0000",
    "levtype" : "pl",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step" : "0",
    "feature" : {
        "type" : "verticalprofile",
        "points": [[-9.10, 38.78]],
        "axes": "levelist",
        "range" : {
            "start" : 0,
            "end" : 1000,
        }
    },
    "format": "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```
The following will return a vertical profile on `2024-10-06 00:00:00` with levels from `0` to `1000` including all levels available in between, for the parameters `164/167/169` at the point given. This data will be returned for each ensemble number requested.

`"polytope"` refers to the underlying service being used to return the data. `"emcwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

## Required Fields

For a vertical profile within the `feature` dictionary three fields are required

* `type`
* `points`

For a vertical profile `type` must be `verticalprofile`.

`points` has to be a nested list with two points corresponding to a latitude and a longitude.


## Optional Fields

`axes` refers to the axes on which to generate the vertical profile. In this case the vertical profile is generated accross `levelist` based on the inputted `range`. In the vertical profile this field is optional as the default is assumed to be `levelist` if not given.

`range` is an optional field within `feature`. It refers to the extent of the `axes` on which the vertical profile will be generated. In the above case where:

```python
    "axes": "levelist",
    "range" : {
        "start" : 0,
        "end" : 1000,
    }
```

A vertical profile accross `levelist` will start at level `0` and end at level `1000` with all levels found in between being included. `range` can also contain `interval`.

```python
    "axes": "levelist",
    "range" : {
        "start" : 0,
        "end" : 1000,
        "interval" : 2,
    }
```
In this case every second level will be returned if it exists.

As `range` is an optional field it can be left out, however there is not a default value. Instead the user has to include the vertical profile `axes` in the main body of the request like below:

```python
request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20241006",
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "levelist" : "0/to/1000",
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axes": "levelist",
    },
    "format": "covjson",
}
```

This is equivalent to the first request presented. 

At least one of `range` or `levelist` must be included in the request, but not both. In this case an error will be provided telling the user that `levelist` is overspecified.

Conversely at least one of `range` or `levelist` must be included.

