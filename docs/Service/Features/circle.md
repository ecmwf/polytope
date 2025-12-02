# Circle

## Basic Example

An example of a circle requested via earthkit-data:

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
    "step" : "0",
    "feature" : {
        "type" : "circle",
        "center": [[-9.10, 38.78]],
        "radius": 0.1,
    },
    "format": "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```
The following will return a circle centered at the point provided with a radius of `0.1` in degrees, starting yesterday at 00Z with step `0`, for the parameters `164/167/169` at the point given. This data will be returned for each ensemble number requested.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

## Required Fields

For a circle within the `feature` dictionary three fields are required

* `type`
* `center`
* `radius`

For a circle `type` must be `circle`.

`center` must be a nested list with a point containing a `latitude` and a `longitude`.

`radius` refers to the radius of the requested circle in the form of degrees and is a single value.


## Optional Fields

`axes` can also be provided which defines the spatial `axes` on which the request is made. For example if the user provides points in the order `longitude`, `latitude` they can add `axes` : `["longitude", "latitude"]`.
