# Polygon

## Basic Example

<!-- ### Polytope-mars

A basic example of requesting a polygon using polytope-mars:

```python
from polytope_mars.api import PolytopeMars

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20240930",
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1",
    "step": "0",
    "feature" : {
        "type" : "polygon",
        "shape" : [[-1, 1], [-1, 0], [0, 1], [-1, 1]],
	},
    "format" : "covjson",
}

result = PolytopeMars().extract(request)
```

This request will return all points contained in `shape` for with forecast date of `20240930T000000` for `step` `0`, ensemble `number` `1` and the three prvoided parameters.

Notes: 
* The data has to exist in the data source pointed to in the config.
* No config is provided via the PolytopeMars interface so a config will be loaded from the default locations. The config can also be passed directly via the interface.

### Earthkit-data -->

An example polygon requested via Earthkit-data:

```python
from polytope_mars.api import PolytopeMars

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20240930",
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1",
    "step": "0",
    "feature" : {
        "type" : "polygon",
        "shape" : [[-1, 1], [-1, 0], [0, 1], [-1, 1]],
	},
    "format" : "covjson",
}

result = PolytopeMars().extract(request)
```

This request will return all points contained in `shape` for with forecast date of `20240930T000000` for `step` `0`, ensemble `number` `1` and the three prvoided parameters.

`"polytope"` refers to the underlying service being used to return the data. `"emcwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

Notes: 
* The data has to exist in the fdb on the polytope server.
* No config is required to be passed when using this method, it is generated on the server side.
* Further details on the `from_source` method can be found here: https://earthkit-data.readthedocs.io/en/latest/guide/sources.html

## Required Fields

For a polygon within the `feature` dictionary two fields are required

* `type`
* `shape`

For a polygon `type` must be `polygon`.

The values in `points` must correspond to a latitude and a longitude. The first point and last point must also be the same to complete the polygon.

The polygon feature also has a max number of points that can be requested in the perimeter of the polygon, and the max area of the polygon is also constrained based on the vonfig provided.

`shape` can also take multiple polygons in a single request in the following form:

```python
"shape" : [[[-1, 1], [-1, 0], [0, 1], [-1, 1]], [[-2, 2], [-2, 1], [1, 2], [-2, 2]]],
```

User can also request ranges for other keys such as `number`. In this case the polygon cutout will be returned for each of the values requested.

```python
from polytope_mars.api import PolytopeMars

request = {
    "class" : "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20240930",
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0079", 
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

result = PolytopeMars().extract(request)
```

The returned values will be:

* `number: 1, step: 0, Points within shape`
* `number: 1, step: 1, Points within shape`
* `number: 2, step: 0, Points within shape`
* `number: 2, step: 1, Points within shape`


## Optional Fields

