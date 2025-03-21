# Polygon

## Basic Example

An example polygon requested via earthkit-data:

```python
import earthkit.data

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,  # Note: date must be within the last two days
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1",
    "step": "0",
    "feature" : {
        "type" : "polygon",
        "shape" : [[-1, 1], [-1, 0], [0, 1]],
	},
    "format" : "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

This request will return all points contained in `shape` from yesterday's 00Z forecast for `step` `0`, ensemble `number` `1` and the three provided parameters.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.


## Required Fields

For a polygon two fields are required within the `feature` dictionary

* `type`
* `shape`

For a polygon `type` must be `polygon`.

The values in `points` must correspond to a latitude and a longitude. The first point is assumed to be the last point, however users can also provide the last point in the request to complete the polygon.

The polygon feature also has a max number of points that can be requested in the perimeter of the polygon, and the max area of the polygon is also constrained based on the config provided.

`shape` can also take multiple polygons in a single request in the following form:

```python
"shape" : [[[-1, 1], [-1, 0], [0, 1], [-1, 1]], [[-2, 2], [-2, 1], [1, 2], [-2, 2]]],
```

User can also request ranges for other keys such as `number`. In this case the polygon cutout will be returned for each of the values requested.

```python
request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/2",
    "step": "0/1",
    "feature" : {
        "type" : "polygon",
        "shape" : [[-1, 1], [-1, 0], [0, 1], [-1, 1]],
	},
    "format" : "covjson",
}
```

The returned values will be:

* `number: 1, step: 0, Points within shape`
* `number: 1, step: 1, Points within shape`
* `number: 2, step: 0, Points within shape`
* `number: 2, step: 1, Points within shape`

