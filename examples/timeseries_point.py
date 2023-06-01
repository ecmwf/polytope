import numpy as np

# import plotly
# import plotly.graph_objects as go
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Select, Span

# from PIL import Image


def format_stats_nicely(stats):
    for key in stats.keys():
        print(key)
        print("-----------------------" + "\n")
        actual_stats = stats[key]
        actual_stats_keys = list(actual_stats.keys())
        print(str(actual_stats_keys[0]) + "\t" + str(actual_stats_keys[1]) + "\t" + str(actual_stats_keys[2])
              + "\t" + str(actual_stats_keys[3]))
        print(str(actual_stats[actual_stats_keys[0]]) + "\t" + str(actual_stats[actual_stats_keys[1]]) + "\t"
              + str(actual_stats[actual_stats_keys[2]]) + "\t" + str(actual_stats[actual_stats_keys[3]]))
        print("\n")


class Test:
    def setup_method(self):
        array = xr.open_dataset("./examples/data/temp_model_levels.grib", engine="cfgrib")
        options = {"longitude": {"Cyclic": [0, 360.0]}}
        self.xarraydatacube = XArrayDatacube(array)
        for dim in array.dims:
            array = array.sortby(dim)
        self.array = array
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer, options=options)

    def test_slice_shipping_route(self):

        request = Request(Select("latitude", [49]), Select("longitude", [2]), Span("step", np.timedelta64(0, "s"), np.timedelta64(3600, "s")), Select("hybrid", [0]))
        result, stats = self.API.retrieve_debugging(request)
        print("stats")
        print("=====================")
        print("\n")
        format_stats_nicely(stats)
