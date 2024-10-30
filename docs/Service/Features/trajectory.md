# Trajectory

## Basic Example

<!-- ### Polytope-mars

A basic example of requesting a trajectory using polytope-mars:

```python
from polytope_mars.api import PolytopeMars

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20240930",
    "time" : "0000",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "levtype" : "pl",
    "number" : "1",
    "feature" : {
        "type" : "trajectory",
        "points" : [[-1, -1, 1000, 0], [0, 0, 1000,  12], [1, 1, 250, 24]],
	},
    "format" : "covjson",
}

result = PolytopeMars().extract(request)
```

This request will return a trajectory with forecast date of `20240930T000000` for the three requested parameters for the points:

* `lat: -1, long: -1, pressure level: 1000, step: 0`
* `lat: 0, long: 0, pressure level: 1000, step: 12`
* `lat: 1, long: 1, pressure level: 250, step: 24`

The `trajectory` `feature` also contains another field called `padding` with a default of 1. This is the radius of the circle swept around the trajectory where points within this radius are returned to the user.

Notes: 
* The data has to exist in the data source pointed to in the config.
* No config is provided via the PolytopeMars interface so a config will be loaded from the default locations. The config can also be passed directly via the interface.

### Earthkit-data -->

An example trajectory requested via Earthkit-data:

```python
import earthkit.data

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20240930",
    "time" : "0000",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "levtype" : "pl",
    "number" : "1",
    "feature" : {
        "type" : "trajectory",
        "points" : [[-1, -1, 1000, 0], [0, 0, 1000,  12], [1, 1, 250, 24]],
	},
    "format" : "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

This request will return a trajectory with forecast date of `20240930T000000` for the three requested parameters for the points:

* `lat: -1, long: -1, pressure level: 1000, step: 0`
* `lat: 0, long: 0, pressure level: 1000, step: 12`
* `lat: 1, long: 1, pressure level: 250, step: 24`

The `trajectory` `feature` also contains another field called `padding` with a default of 1. This is the radius of the circle swept around the trajectory where points within this radius are returned to the user.

`"polytope"` refers to the underlying service being used to return the data. `"emcwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

Notes: 
* The data has to exist in the fdb on the polytope server.
* No config is required to be passed when using this method, it is generated on the server side.
* Further details on the `from_source` method can be found here: https://earthkit-data.readthedocs.io/en/latest/guide/sources.html

## Required Fields

For a trajectory within the `feature` dictionary two fields are required

* `type`
* `points`
* `padding`

For a trajectory `type` must be `trajectory`.

The values in `points` can change depending on the `axes`. The default for `axes` is:

```python
"axes" : ["lat", "long", "level", "step"]
```

In this default case a nested list of at least two points with values for `lat`, `long`, `level`, and `step` must be provided. 

Another required field that is within the `feature` dictionary is `padding`. This refers to the radius of the circle swept around the trajectory along which points will be included.


## Optional Fields

`axes` refers to the axes on which to generate the trajectory. As stated above the minimum default `axes` contains `lat`, `long`, `level`, and `step` meaning if `axes` is not included these values must be provided per point.

However `axes` can also be provided by the user and with less values. The minimum values of `axes` are:

```python
"axes" : ["lat", "long"]
```

In this case only `lat` and `long` must be provided in the requested points but a level and time axis must be provided in the main body of the request. These values will be propogated for each set of `lat`, `long` points. For example in the following request:

```python
request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20240930",
    "time" : "0000",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "levtype" : "pl",
    "levelist" : "500",
    "number" : "1",
    "step" : "0/1"
    "feature" : {
        "type" : "trajectory",
        "points" : [[-1, -1], [0, 0], [-1, -1]],
        "axis" : ['lat', 'long']
	},
}
```

The following points would be returned:

* `lat: -1, long: -1, pressure level: 500, step: 0`
* `lat: 0, long: 0, pressure level: 500, step: 0`
* `lat: 1, long: 1, pressure level: 500, step: 0`
* `lat: -1, long: -1, pressure level: 500, step: 1`
* `lat: 0, long: 0, pressure level: 500, step: 1`
* `lat: 1, long: 1, pressure level: 500, step: 1`

The user does not have to give `step` as the time axis. In the case of a climate dataset `datetime` can also be used.

Combinations such as `"axis" : ['lat', 'step']` will return an error. 

If `step` is included as an `axis` and also in the main body of teh request. An error that the request is overspecified will also be thrown.