# Quick Start

Once a user has installed Earthkit-data and has their credentials in place, it is very easy to make a simple request.

An example of a time-series requested via Earthkit-data:

```python
import earthkit.data

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
        "axes": "step",
        "range" : {
            "start" : 0,
            "end" : 360,
        }
    },
    "format": "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```
The following will return a timeseries starting on `2024-10-06 00:00:00` with steps from `0` to `360` including all steps available in between, for the parameters `164/167/169` at the point given. This data will be returned for each ensemble number requested.

`"polytope"` refers to the underlying service being used to return the data. `"emcwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

To view the returned covjson run:

```
ds._json()
```

To convert your covjson into an xarray the following can  be done:

```
ds.to_xarray()
```

For more information about each feature see the following pages:

### <a href="../Features/feature">Features</a>
  - <a href="../Features/timeseries">Timeseries</a>
  - <a href="../Features/vertical_profile">Vertical Profile</a>
  - <a href="../Features/polygon">Polygon</a>
  - <a href="../Features/boundingbox">Bounding Box</a>
  - <a href="../Features/trajectory">Trajectory</a>