import time

import pandas as pd

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope, Request
from polytope.shapes import All, Point, Select

time1 = time.time()
# Create a dataarray with 3 labelled axes using different index types
options = {
    "values": {
        "transformation": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}}
    },
    "date": {"transformation": {"merge": {"with": "time", "linkers": ["T", "00"]}}},
    "step": {"transformation": {"type_change": "int"}},
    "number": {"transformation": {"type_change": "int"}},
    "longitude": {"transformation": {"cyclic": [0, 360]}},
}
config = {"class": "od", "expver": "0001", "levtype": "sfc", "type": "pf"}
fdbdatacube = FDBDatacube(config, axis_options=options)
slicer = HullSlicer()
self_API = Polytope(datacube=fdbdatacube, engine=slicer, axis_options=options)

time2 = time.time()
request = Request(
    All("step"),
    Select("levtype", ["sfc"]),
    Select("date", [pd.Timestamp("20231205T000000")]),
    Select("domain", ["g"]),
    Select("expver", ["0001"]),
    Select("param", ["167"]),
    Select("class", ["od"]),
    Select("stream", ["enfo"]),
    Select("type", ["pf"]),
    # Select("latitude", [0.035149384216], method="surrounding"),
    Point(["latitude", "longitude"], [[0.04, 0]], method="surrounding"),
    All("number"),
)
result = self_API.retrieve(request)
print(time.time() - time1)
print(time.time() - time2)
print(len(result.leaves))
