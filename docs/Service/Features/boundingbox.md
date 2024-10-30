# Bounding Box

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
        "type" : "boundingbox",
        "points" : [[-1, -1], [1, 1]],
	},
    "format" : "covjson",
}

result = PolytopeMars().extract(request)
```

This request will return a bounding box with forecast date of `20240930T000000` for the three requested parameters for the points within a bounding box with top left coordinate at latitude -1 and longitude -1, and bottom right point at latitude 1 and longitude 1.



Notes: 
* The data has to exist in the data source pointed to in the config.
* No config is provided via the PolytopeMars interface so a config will be loaded from the default locations. The config can also be passed directly via the interface.

### Earthkit-data -->

An example bounding box requested via Earthkit-data:

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
    "levtype" : "sfc",
    "number" : "1",
    "feature" : {
        "type" : "boundingbox",
        "points" : [[-1, -1], [1, 1]],
	},
    "format" : "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```

This request will return a bounding box with forecast date of `20240930T000000` for the three requested parameters for the points within a bounding box with top left coordinate at latitude -1 and longitude -1, and bottom right point at latitude 1 and longitude 1.

`"polytope"` refers to the underlying service being used to return the data. `"emcwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

Notes: 
* The data has to exist in the fdb on the polytope server.
* No config is required to be passed when using this method, it is generated on the server side.
* Further details on the `from_source` method can be found here: https://earthkit-data.readthedocs.io/en/latest/guide/sources.html

## Required Fields

For a boundingbox within the `feature` dictionary two fields are required

* `type`
* `points`

For a bounding box `type` must be `boundingbox`.

`points` must contain two points, the first corresponding to the top left of the requested box, and the second correspongin to the bottom right coordinate. By default they should only contain a latitude and longitude. However as seen below this can be changed with the `axes` key.


## Optional Fields

`axes` refers to the axes on which to generate the bounding box. As stated above the minimum default `axes` contains `lat` and `long` meaning if `axes` is not included these values must be provided per point. By default the level is taken from the main body of the request.

However `axes` can also be provided by the user and with a value for level. Such as here:

```python
"axes" : ["lat", "long", "level"]
```

In this case the user must provide a `lat`, `long` and `level`. `level` should not be included in the main body of the request in this case. An example can be seen here:


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
    "number" : "1",
    "feature" : {
        "type" : "boundingbox",
        "points" : [[-1, -1, 1000], [1, 1, 500]],
        "axes" : ["lat", "long", "level"],
	},
    "format" : "covjson",
}
```

For this request a bounding box with top left corner at lat -1, long -1 and pressure level 1000, and bottom right corner at lat 1, long 1, and pressure level 500.

Without level in the `axes` this will be taken from the main body of the request. In the case of `levtype` = `sfc`, no levelist is required.