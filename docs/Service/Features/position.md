# Position

## Basic Example

An example of a position requested via earthkit-data:

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
    "number" : "1",
    "step" : "0"
    "feature" : {
        "type" : "position",
        "points": [[-9.10, 38.78]],
    },
    "format": "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```
The following will return a position starting yesterday at 00Z with step `0`, for the parameters `164/167/169` at the point given. This data will be returned for ensemble member `1`.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

## Required Fields

For a position within the `feature` dictionary two fields are required

* `type`
* `points`

For a position `type` must be `position`.

`points` must be a nested list with a points containing a latitude and a longitude.

## Optional Fields

`axes` can also be provided which defines the spatial `axes` on which the request is made. For example if the user provides points in the order `longitude`, `latitude` they can add `axes` : `["longitude", "latitude"]`.

