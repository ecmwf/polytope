# Quick Start

Once a user has installed earthkit-data and has their credentials in place, you can make a simple request.

An example of a time-series requested via earthkit-data:

```python
import earthkit.data

request = {
    "class": "od",
    "stream" : "enfo",
    "type" : "pf",
    "date" : "20241006",
    "time" : "0000",
    "levtype" : "sfc",
    "expver" : "0001", 
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
    "format": "covjson",
}

ds = earthkit.data.from_source("polytope", "ecmwf-mars", request, stream=False, address='polytope.ecmwf.int')
```
The following will return a timeseries starting on `2024-10-06 00:00:00` with steps from `0` to `360` including all steps available in between, for the parameters `164/167/169` at the point given. This data will be returned for each ensemble number requested.

`"polytope"` refers to the underlying service being used to return the data. `"ecmwf-mars"` is the dataset we are looking to retrieve from. Setting `stream=False` returns all the requested data to us once it is available. `address` points to the endpoint for the polytope server.

To view the returned covjson run:

```python
ds._json()
```

To convert your covjson into an xarray the following can be done:

```python
ds.to_xarray()
```

The following visualisation does not use the latest version of earthkit-plots. To replicate it you need to install the https://github.com/ecmwf/earthkit-plots/tree/feature/ams-meteograms branch

```python
import ipywidgets as widgets
import earthkit.plots
import earthkit.data

TIME_FREQUENCY = "6H"

def f():
    data = ds
    chart = earthkit.plots.Chart()
    chart.box(data, time_frequency=TIME_FREQUENCY)
    chart.line(data, time_frequency=TIME_FREQUENCY, aggregation="mean", line_color="purple")
    chart.show()

out = widgets.interactive_output(f, {})
display(out)
```

For more information about each feature see the <a href="../Features/feature">Features</a> page.