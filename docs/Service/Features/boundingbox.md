# Bounding Box

## Basic Example

An example bounding box requested via earthkit-data:

```python
import earthkit.data

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,  # Note: date must be within the last two days
    "time" : "0000",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "levtype" : "sfc",
    "number" : "1",
    "step" : "0", 
    "feature" : {
        "type" : "boundingbox",
        "points" : [[-1, -1], [1, 1]],
	},
    "format" : "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

This request will return a bounding box from yesterday's midnight forecast for the three requested parameters for the points within a bounding box with top left coordinate at latitude -1 and longitude -1, and bottom right point at latitude 1 and longitude 1.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.


## Required Fields

For a bounding box, two fields are required within the `feature` dictionary

* `type`
* `points`

For a bounding box, `type` must be `boundingbox`.

`points` must contain two points, the first corresponding to the top left of the requested box, and the second corresponding to the bottom right coordinate. By default they should only contain a latitude and longitude. However as seen below this can be changed with the `axes` key.


## Optional Fields

`axes` refers to the axes on which to generate the bounding box. As stated above the minimum default `axes` contains `latitude` and `longitude` meaning if `axes` is not included these values must be provided per point. By default the level is taken from the main body of the request.

However `axes` can also be provided by the user and with a value for level. Such as here:

```python
"axes" : ["latitude", "longitude", "levelist"]
```

In this case the user must provide a `latitude`, `longitude` and `levelist`. `levelist` should not be included in the main body of the request in this case. An example can be seen here:


```python
request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,
    "time" : "0000",
    "levtype" : "pl",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "203/133",
    "number" : "1",
    "step" : "0",
    "feature" : {
        "type" : "boundingbox",
        "points" : [[-0.1, -0.1, 500], [0.1, 0.1, 1000]],
        "axes" : ["latitude", "longitude", "levelist"]
	},
    "format" : "covjson"
}
```

For this request, a bounding box with top left corner at lat -1, lon -1 and pressure level 1000, and bottom right corner at lat 1, lon 1, and pressure level 500.

Without level in the `axes` this will be taken from the main body of the request. In the case of `levtype` = `sfc`, no levelist is required.