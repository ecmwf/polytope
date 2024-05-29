import time

import pandas as pd

from polytope.datacube.backends.fdb import FDBDatacube
from polytope.polytope import Polytope, Request
from polytope.shapes import All, Point, Select

time1 = time.time()
# Create a dataarray with 3 labelled axes using different index types
options = {
    "values": {"mapper": {"type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}},
    "date": {"merge": {"with": "time", "linkers": ["T", "00"]}},
    "step": {"type_change": "int"},
    "number": {"type_change": "int"},
    "longitude": {"cyclic": [0, 360]},
    "latitude": {"reverse": {True}},
}

config = {"class": "od", "expver": "0001", "levtype": "sfc", "type": "pf"}
fdbdatacube = FDBDatacube(config, axis_options=options)
self_API = Polytope(datacube=fdbdatacube, axis_options=options)

print(time.time() - time1)

total_polytope_time = 0
for i in range(10):
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
time3 = time.time()
result = self_API.retrieve(request)
time4 = time.time()
print(time.time() - time1)
print(time.time() - time2)
print(time4 - time3)
print(len(result.leaves))
print([len(leaf.result) for leaf in result.leaves])
result.pprint()
