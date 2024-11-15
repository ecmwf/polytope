# Trajectory

## Basic Example

An example trajectory requested via earthkit-data:

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/166/167/169",
    "number" : "1",
    "step": "0",
    "feature" : {
        "type" : "trajectory",
        "points" : [[-0.1, -0.1], [0, 0], [0.1, 0.1]],
        "radius" : 0.1,
        "axes" :["latitude", "longitude"],
	},
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

This request will return a trajectory from yesterday's midnight forecast  for the three requested parameters for the points along the path gives with a radius of 0.1.

The `trajectory` `feature` also contains another field called `radius`. This is the radius of the circle swept around the trajectory where points within this radius are returned to the user.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

## Required Fields

For a trajectory two fields are required within the `feature` dictionary 

* `type`
* `points`
* `radius`

For a trajectory `type` must be `trajectory`.

The values in `points` can change depending on the `axes`. `axes` can contain the following values:

```python
"axes" : ["latitude", "longitude", "levelist", "step"]
```

In this default case, a nested list of at least two points with values for `latitude` and `longitude` must be provided. 

Another required field that is within the `feature` dictionary is `radius`. This refers to the radius of the circle swept around the trajectory along which points will be included.


## Optional Fields

`axes` refers to the axes on which to generate the trajectory. As stated above the minimum default `axes` contains `latitude`, `longitude` meaning if `axes` is not included these values must be provided per point.

However `axes` can also be provided by the user and with more values:

```python
"axes" : ["latitude", "longitude", "levelist", "step"]
```

In this case a point must contain a value for each axis.
<!---
In this case only `latitude` and `longitude` must be provided in the requested points but a level and time axis must be provided in the main body of the request. These values will be propagated for each set of `latitude`, `longitude` points. For example in the following request:

```python
request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : -1,
    "time" : "0000",
    "expver" : "0001", 
    "domain" : "g",
    "param" : "164/167/169",
    "levtype" : "pl",
    "levelist" : "500",
    "number" : "1",
    "step" : "0/1"
    "feature" : {
        "type" : "trajectory",
        "points" : [[-1, -1], [0, 0], [-1, -1]],
        "axes" : ['latitude', 'longitude']
	},
}
```

The following points would be returned:

* `lat: -1, lon: -1, pressure level: 500, step: 0`
* `lat: 0, lon: 0, pressure level: 500, step: 0`
* `lat: 1, lon: 1, pressure level: 500, step: 0`
* `lat: -1, lon: -1, pressure level: 500, step: 1`
* `lat: 0, lon: 0, pressure level: 500, step: 1`
* `lat: 1, lon: 1, pressure level: 500, step: 1`

The user does not have to give `step` as the time axis. In the case of a climate dataset `datetime` can also be used.

Combinations such as `"axis" : ['lat', 'step']` will return an error if `step` is included as an `axis` and also in the main body of the request. An error that the request is overspecified will also be thrown.
-->