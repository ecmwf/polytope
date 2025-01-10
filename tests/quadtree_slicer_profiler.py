import cProfile

import numpy as np
import pygribjump as gj

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import Box

options = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        {
            "axis_name": "date",
            "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        },
        {
            "axis_name": "values",
            "transformations": [
                {"name": "mapper", "type": "irregular", "resolution": 1280, "axes": ["latitude", "longitude"]}
            ],
        },
    ],
    "compressed_axes_config": [
        "longitude",
        "latitude",
        "levtype",
        "step",
        "date",
        "domain",
        "expver",
        "param",
        "class",
        "stream",
        "type",
    ],
    "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
}
fdbdatacube = gj.GribJump()

x = np.linspace(0, 100, 1000)
y = np.linspace(0, 100, 1000)
# create the mesh based on these arrays
X, Y = np.meshgrid(x, y)
X = X.reshape((np.prod(X.shape),))
Y = Y.reshape((np.prod(Y.shape),))
coords = zip(X, Y)
points = [list(coord) for coord in coords]
polytope = Box(["latitude", "longitude"], [1, 1], [20, 30]).polytope()[0]
API = Polytope(
    request=Request(polytope),
    datacube=fdbdatacube,
    options=options,
    engine_options={"latitude": "quadtree", "longitude": "quadtree"},
    point_cloud_options=points,
)
cProfile.runctx(
    "API.engines['quadtree'].extract(API.datacube, [polytope])", globals(), locals(), "profiled_extract_quadtree.pstats"
)
