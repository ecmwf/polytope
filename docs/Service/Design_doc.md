# Polytope-mars

## Feature Documentation

### Feature Keyword

Feature extraction expands existing mars requests to include a `feature` keyword that includes a json dictionary that describes the given feature. This feature is then extracted using the Polytope feature extraction algorithm and only points within the given feature are returned.

```python
"feature" : {
    "type" : "timeseries",
    "points" : [[-9.109280931080349, 38.78655345978706]],
}
```

#### Type

An example of a minimal feature of `type` : `timeseries` can be seen above. A feature dictionary must always contain a `type`. The `type` in this case refers to what feature is being requested, the `type` of feaature requested will then determine the format of the output returned, what other keys can go in the feature and suitable defaults if they are not available. In some cases it may also affect keys outside of the feature dictionary that come from the traditional mars request. For example if `type` : `verticalprofile` and `levtype` : `sfc`, this request will not be sent as a vertical profile expects either `levtype` : `pl/ml`. Other exceptions will be given for each separate feature `type`.

The value available for `type` currently are as follows:

* `timeseries`
* `verticalprofile`
* `polygon`
* `trajectory`
* `frame`
* `boundingbox`

More feature types will be added in the future.

#### Geometry

A feature dictionary must also contain the requested geometry in some form. For a `timeseries` as seen above this comes in the form `points` which requests a timeseries at a given point, however this geometry is not always a point and depends upon `type`. The geometry is a mandatory field for all features.

#### Axis

A non-mandatory field that is available for each feature that is not present in the above example is `axis`. `axis` determines what field that the data should be enumerated along. In the case of a `timeseries` this will default to `step` meaning that the timeseries will be along the `step` axis, however there are other available `axes` such as `datetime`, this would be for climate data which contains no `step` `axis`.

#### Range

`range` is a json dictionary that is available for some features, it contains the extents of a given a `axes`. For example:

```python
"range" : {
    "start" : 0,
    "end" : 10,
    "interval" : 2,
}
```

If this range was included in the above feature dictionary for a `timeseries` it would ask for `step` (due to it being the default axis for timeseries) starting at `0` and ending at `10` with an interval of `2`, the returned steps would be `0,2,4,6,8,10`. This is equivalent to asking for the following in a mars request:

```python
"step" : "0/to/10/by/2"
```

The above can also be put in the body of the request. However it must then be mutually exclusive with `range`. If both or neither are in the request an error is thrown.

`range` can also appear in the following form:

```python
"range" : [0,1,4,7,10]
```

This will only return the asked steps similar to in a MARS request where a user asks for the following:

```python
"step" : "0/1/4/7/10"
```

Again either a `range` within the feature or an explicit `step` within the main body of the request can be used but not both or neither as there is no suitable default value unlike MARS.


### MARS Fields

The non `feature` elements of the polytope-mars request act similar to the way one would expect when creating a MARS request with a few differences.

* Most fields do not have a default value that will be tried if the field is not in the request.
* If a user makes a request and data is only available for some of the fields requested an error will be returned. Users will either receive all the data they requested or none.
* All key/value pairs must be in the form of a string n the main body of the request. Only values in the `feature` can be non-string types.
* Fields that can also be in the `feature` dictionary can either be provided in the main body of the request or in the `feature` but not both otherwise an error will be thrown. Both of the following examples are valid.

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
    "step": "0/to/360",
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axis": "step",
    },
}
```

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
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axis": "step",
        "range" : {
            "start" : 0,
            "end" : 360,
        }
    },
}
```

However the following is not:

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
    "step" : "0/to/360",
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axis": "step",
        "range" : {
            "start" : 0,
            "end" : 360,
        }
    },
}
```

The above would throw an error that `step` has been over-subscribed.

Ideally an valid mars request should be able to accept a valid `feature` and the polytope-mars request be valid but this may not always be true.

Users can include the `format` key. However, initally the only value available will be `covjson` or `application/json+covjson`, these will be the default values if `format` is not included. Further formats may be added in the future.

### Features

The following features will be available for use in polytope-mars.

#### Timeseries

A timeseries request has a `feature` with `type` : `timeseries` and a geometry in the form of `points` containing a single point with latitude and longitude values. It also requires at least one time dimension with the default being `step`, although `datetime` is also accepted. The following is an example of a timeseries request:

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
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axis": "step",
        "range" : {
            "start" : 0,
            "end" : 360,
        }
    },
}
```

This is equivilent to:

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
    "step" : "0/to/360",
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axis": "step",
    },
}
```

In this case the user is requesting `step` `0-360` on `20241006` for the point `[-9.10, 38.78]`. As the user does not specify `interval` all steps between `0-360` that are available. If the datacube is a climate dataset that does not contain step, an error would be thrown as `step` is not in the datacube. In this case the user would have to provide a request like the following:

```python
request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "levtype" : "sfc",
    "expver" : "0079", 
    "domain" : "g",
    "param" : "164/167/169",
    "number" : "1/to/50",
    "step" : "0/to/360",
    "feature" : {
        "type" : "timeseries",
        "points": [[-9.10, 38.78]],
        "axis": "datetime",
        "range": {
            "start" : "20241006T000000",
            "end" : "20241009T000000",
        }
    },
}
```

Here a user will receive a `timeseries` for the dates `20241006T000000` to `20241009T000000` but not including the final date. The user can also provide an `interval` like `1d` meaning only intervals of 1 day are provided so in this case the following datetimes are returned.

* `20241006T000000`
* `20241007T000000`
* `20241008T000000`

If a dataset contains both a `step` and `datetime` the user can still request `axis` : `datetime`, and this request will return a timeseries across `datetime` rather than `step`.

In the above case if a range is provided for a field such as `number` a time series as described above will be provided per `number` or any other range field.

CoverageJSON output type: PointSeries

#### Vertical Profile

A vertical profile request has a `feature` with `type` : `verticalprofile` and a geomtry in the form of `points` containing a single point with latitude and longitude values. It also requires a `levtype` that is not `sfc` and a `levelist` in the request or as part of the `feature`. The following is an example of a vertical profile request:

```python
request = {
    "class": "od",
    "stream": "enfo",
    "type": "pf",
    "date": "20240925",
    "time": "0000",
    "levtype": "pl",
    "expver": "0079",
    "domain": "g",
    "param": "203/133",
    "number": "1",
    "step": "0",
    "levelist": "1/to/1000",
    "feature": {
        "type": "verticalprofile",
        "points": [[38.9, -9.1]],
    },
}
```

The following is equivilent to the above:

```python
request = {
    "class": "od",
    "stream": "enfo",
    "type": "pf",
    "date": "20240925",
    "time": "0000",
    "levtype": "pl",
    "expver": "0079",
    "domain": "g",
    "param": "203/133",
    "number": "1",
    "step": "0",
    "levelist": "1/to/1000",
    "feature": {
        "type": "verticalprofile",
        "points": [[38.9, -9.1]],
        "range" : {
            "start" : 1,
            "end" : 1000
        }
    },
}
```

`levtype` can either be `ml` or `pl` but atleast one must be present.

`levelist` can either be in the main body of the request or in `range` as described in the `range` section. If no `interval` is provided all values in from `start` to `end` will be requested.

Currently the default for `axes` is `levelist` and is the only valid value for this key. This may change in the future. Users can include this in the request but it is not necessary.

In the above case if a range is provided for a field such as `number`, a vertical profile as described above will be provided per `number` or any other range field.

CoverageJSON output type: VerticalProfile

#### Trajectory

A trajectory request has a `feature` with `type` : `trajectory` and a geomtry in the form of `points` containing atleast two points with latitude and longitude, a level value, and a time value if no `axes` is provided. This is because the default `axes` are as follows:

```python
"axes" : ["lat", "long", "level", "step"]
```

An example using default `axes` if found below.

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
        "type" : "trajectory",
        "points" : [[-1, -1, 1000, 0], [0, 0, 1000,  12], [1, 1, 250, 24]],
	},
}
```

This request will return a trajectory with forecast date of `20240930T000000` for the three requested parameters for the points:

* `lat: -1, long: -1, pressure level: 1000, step: 0`
* `lat: 0, long: 0, pressure level: 1000, step: 12`
* `lat: 1, long: 1, pressure level: 250, step: 24`

The `trajectory` `feature` also contains another field called `padding` with a default of 1. This is the radius of the circle swept around the trajectory where points within this radius are returned to the user.

`axes` must contain at minimum `lat` and `long` however a time and level axes are optional if provided in the main body of the request. The level and time axes can also take different values such as `step` or `datetime` for the time axes. 

The following is an example of a combination of `axes` that will cause an error:

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
        "type" : "trajectory",
        "points" : [[-1, 0], [0, 12], [1, 24]],
        "axis" : ['lat', 'step']
	},
}
```
This is due to the fact that `long` is required to be in `axis`.

A valid example of leaving out a time `axis` is as follows:

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
    "step" : "0/1"
    "feature" : {
        "type" : "trajectory",
        "points" : [[-1, -1, 1000], [0, 0, 1000], [-1, -1, 250]],
        "axis" : ['lat', 'long', 'level']
	},
}
```

In this case the following data will be returned.

* `lat: -1, long: -1, pressure level: 1000, step: 0`
* `lat: 0, long: 0, pressure level: 1000, step: 0`
* `lat: 1, long: 1, pressure level: 250, step: 0`

* `lat: -1, long: -1, pressure level: 1000, step: 1`
* `lat: 0, long: 0, pressure level: 1000, step: 1`
* `lat: 1, long: 1, pressure level: 250, step: 1`

These will be two of the same trajectories but on different steps.

If `step` however was not specified outside of the `feature` the above would give an error that the time `axis` is underspecified.

For any other ranged fields provided in the main request this will replicate the above returned data but per value. For example if ensemble `number` : `1/2` the same data as above would be provided for each `number`.

CoverageJSON output type: Trajectory

#### Polygon

A polygon request has a `feature` with `type` : `poylgon` and a geomtry in the form of `shape` containing atleast one list containing three points with latitude and longitude with the first and final point being the same to complete the polygon. The user can provide multiple lists of points forming polygons in the same request. An example of the `polygon` feature is seen below:

```python
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
}
```

If a user requests a a range for any of `step`, `number`, or `date` a polygon cutout for each field will be returned with a cutout of the data within the polygon. For example:

```python
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
}
```

This request will return a polygon for each number and each step within that given number. 
Returned coverages as polygons:

* `number: 1, step: 0, Points within shape`
* `number: 1, step: 1, Points within shape`
* `number: 2, step: 0, Points within shape`
* `number: 2, step: 1, Points within shape`

Each of these will be an individual coverage with the 3 requested parameters.

The `polygon` feature currently has limits on the size of a returned polygon and the maximum number of points allowed for a requested polygon.

CoverageJSON output type: MultiPoint

### Covjson


CoverageJSON has a number of different output features. Depending on the feature selected the output type will vary.

A coverageCollection is always returned even if there is only a single coverage. 
A new coverage is created for each ensemble number and depending on the feature type each new date (except in timeseries). The only grouped field is `param` which will be in the same coverage.