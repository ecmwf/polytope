import json

import geopandas as gpd
import matplotlib.pyplot as plt
import numpy as np
import xarray as xr

from polytope.datacube.xarray import XArrayDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import Box, Path


class Test:
    def setup_method(self):
        array = xr.open_dataset("./examples/data/output4.grib", engine="cfgrib")
        self.xarraydatacube = XArrayDatacube(array)
        self.array = array
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_slice_shipping_route(self):
        # First give in the travel points of the shipping route in format: lat/long/time( in step right now)
        travel_points = [
            [29.9, 39.8, np.timedelta64(3600, "s")],
            [30.8, 40.5, np.timedelta64(3600, "s")],
            [31.3, 41.4, np.timedelta64(7200, "s")],
        ]

        padded_point_upper = [0.1, 0.1, np.timedelta64(1900, "s")]

        padded_point_lower = [-0.1, -0.1, np.timedelta64(-1900, "s")]
        initial_shape = Box(["latitude", "longitude", "step"], padded_point_lower, padded_point_upper)
        ship_route_polytope = Path(["latitude", "longitude", "step"], initial_shape, *travel_points)

        # For each of these polytopes, extract them and get the results of the extracted points
        request = Request(ship_route_polytope)
        result = self.API.retrieve(request)  # This gives a Request tree
        result.pprint()

        # Transform the tree to a str format and work on this now, like a user would
        string_tree = result.to_json()

        dict_tree = json.loads(string_tree)

        def dico_human_read(dico):
            string = json.dumps(dico, indent=2)
            print(string)

        dico_human_read(dict_tree)

        steps = []
        lats = []
        longs = []
        params = []
        for axis_key in dict_tree.keys():
            for key in dict_tree[axis_key].keys():
                step = key
                for axis_key2 in dict_tree[axis_key][key]:
                    for key2 in dict_tree[axis_key][key][axis_key2]:
                        lat = key2
                        for axis_key3 in dict_tree[axis_key][key][axis_key2][key2]:
                            for key3 in dict_tree[axis_key][key][axis_key2][key2][axis_key3]:
                                long = key3
                                for param_name in dict_tree[axis_key][key][axis_key2][key2][axis_key3][key3]:
                                    dico = dict_tree[axis_key][key][axis_key2][key2][axis_key3][key3]
                                    param = dico[param_name]
                                steps.append(step)
                                lats.append(lat)
                                longs.append(long)
                                params.append(param)

        parameter_values = np.array(params)
        worldmap = gpd.read_file(gpd.datasets.get_path("naturalearth_lowres"))
        fig, ax = plt.subplots(figsize=(12, 6))
        worldmap.plot(color="lightgrey", ax=ax)

        translated_array = parameter_values - np.min(parameter_values)
        scaling = 1 / np.max(translated_array)
        coloring = translated_array * scaling
        colors = []

        for i in range(len(coloring)):
            colour = [0]
            colour.append(coloring[i])
            colour.append(0)
            colors.append(colour)
        ax.scatter(longs, lats, c=colors)
        plt.show()
