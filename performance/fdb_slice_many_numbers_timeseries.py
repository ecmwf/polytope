import time

import pandas as pd
import pygribjump as gj

from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import All, Point, Select

time1 = time.time()
# Create a dataarray with 3 labelled axes using different index types

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
                {"name": "mapper", "type": "octahedral", "resolution": 1280, "axes": ["latitude", "longitude"]}
            ],
        },
        {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
        {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
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
        "number",
    ],
    "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "type": "pf"},
}
fdbdatacube = gj.GribJump()
self_API = Polytope(datacube=fdbdatacube, options=options)

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
    Point(["latitude", "longitude"], [[0.04, 0]], method="surrounding"),
    All("number"),
)
time3 = time.time()
result = self_API.retrieve(request)
time4 = time.time()
print("Polytope time")
print(self_API.time)
print(time.time() - time1)
print(time.time() - time2)
print(time4 - time3)
print(len(result.leaves))
print([len(leaf.result) for leaf in result.leaves])
result.pprint()
