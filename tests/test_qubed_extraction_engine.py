import time

import pandas as pd
import pygribjump as gj
import requests
from qubed import Qube

from polytope_feature.datacube.backends.qubed import QubedDatacube
from polytope_feature.datacube.datacube_axis import (
    PandasTimedeltaDatacubeAxis,
    PandasTimestampDatacubeAxis,
    UnsliceableDatacubeAxis,
)
from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix_nested import (
    NestedHealpixGridMapper,
)
from polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change import (
    TypeChangeStrToTimedelta,
    TypeChangeStrToTimestamp,
)
from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.engine.qubed_slicer import QubedSlicer
from polytope_feature.polytope import Polytope, Request
from polytope_feature.shapes import ConvexPolytope, Select


def find_relevant_subcube_from_request(request, qube_url):
    # NOTE: final url we want is like:
    # "https://qubed.lumi.apps.dte.destination-earth.eu/api/v1/select/climate-dt/?class=d1&dataset=climate-dt"

    for shape in request.shapes:
        if isinstance(shape, Select):
            qube_url += shape.axis + "="
            for i, val in enumerate(shape.values):
                qube_url += str(val)
                if i < len(shape.values) - 1:
                    qube_url += ","
            qube_url += "&"
    # TODO: remove last unnecessary &
    qube_url = qube_url[:-1]
    return qube_url


fdb_tree = Qube.from_json(
    requests.get("https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate-dt.json").json()
)


combi_polytopes = [
    ConvexPolytope(["param"], [["164"]]),
    ConvexPolytope(["time"], [[pd.Timedelta(hours=0, minutes=0)], [pd.Timedelta(hours=12, minutes=0)]]),
    ConvexPolytope(["resolution"], [["high"]]),
    ConvexPolytope(["type"], [["fc"]]),
    ConvexPolytope(["model"], [["ifs-nemo"]]),
    ConvexPolytope(["stream"], [["clte"]]),
    ConvexPolytope(["realization"], ["1"]),
    ConvexPolytope(["expver"], [["0001"]]),
    ConvexPolytope(["experiment"], [["ssp3-7.0"]]),
    ConvexPolytope(["generation"], [["1"]]),
    ConvexPolytope(["levtype"], [["sfc"]]),
    ConvexPolytope(["activity"], [["scenariomip"]]),
    ConvexPolytope(["dataset"], [["climate-dt"]]),
    ConvexPolytope(["class"], [["d1"]]),
    ConvexPolytope(["date"], [[pd.Timestamp("20220811")], [pd.Timestamp("20220912")]]),
    ConvexPolytope(["latitude", "longitude"], [[0, 0], [0.5, 0.5], [0, 0.5]]),
]

# TODO: add lat and lon axes
datacube_axes = {
    "param": UnsliceableDatacubeAxis(),
    "time": PandasTimedeltaDatacubeAxis(),
    "resolution": UnsliceableDatacubeAxis(),
    "type": UnsliceableDatacubeAxis(),
    "model": UnsliceableDatacubeAxis(),
    "stream": UnsliceableDatacubeAxis(),
    "realization": UnsliceableDatacubeAxis(),
    "expver": UnsliceableDatacubeAxis(),
    "experiment": UnsliceableDatacubeAxis(),
    "generation": UnsliceableDatacubeAxis(),
    "levtype": UnsliceableDatacubeAxis(),
    "activity": UnsliceableDatacubeAxis(),
    "dataset": UnsliceableDatacubeAxis(),
    "class": UnsliceableDatacubeAxis(),
    "date": PandasTimestampDatacubeAxis(),
}

time_val = pd.Timedelta(hours=0, minutes=0)
date_val = pd.Timestamp("20300101T000000")


# TODO: add grid axis transformation
datacube_transformations = {
    "time": TypeChangeStrToTimedelta("time", time_val),
    "date": TypeChangeStrToTimestamp("date", date_val),
    "values": NestedHealpixGridMapper("values", ["latitude", "longitude"], 1024),
}

engine_options = {
    "step": "qubed",
    "date": "qubed",
    "levtype": "qubed",
    "param": "qubed",
    "latitude": "qubed",
    "longitude": "qubed",
    "class": "qubed",
    "time": "qubed",
    "type": "qubed",
    "expver": "qubed",
    "stream": "qubed",
    "dataset": "qubed",
    "model": "qubed",
    "resolution": "qubed",
    "stream": "qubed",
    "realization": "qubed",
    "experiment": "qubed",
    "generation": "qubed",
    "activity": "qubed",
}


options = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "date", "transformations": [{"name": "type_change", "type": "date"}]},
        {"axis_name": "time", "transformations": [{"name": "type_change", "type": "time"}]},
        {
            "axis_name": "values",
            "transformations": [
                {"name": "mapper", "type": "healpix_nested", "resolution": 1024, "axes": ["latitude", "longitude"]}
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
    ],
    # "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
    "pre_path": {"param": "165", "activity": "baseline", "resolution": "high"},
    "datacube_axes": {
        "param": "UnsliceableDatacubeAxis",
        "time": "PandasTimedeltaDatacubeAxis",
        "resolution": "UnsliceableDatacubeAxis",
        "type": "UnsliceableDatacubeAxis",
        "model": "UnsliceableDatacubeAxis",
        "stream": "UnsliceableDatacubeAxis",
        "realization": "UnsliceableDatacubeAxis",
        "expver": "UnsliceableDatacubeAxis",
        "experiment": "UnsliceableDatacubeAxis",
        "generation": "UnsliceableDatacubeAxis",
        "levtype": "UnsliceableDatacubeAxis",
        "activity": "UnsliceableDatacubeAxis",
        "dataset": "UnsliceableDatacubeAxis",
        "class": "UnsliceableDatacubeAxis",
        "date": "PandasTimestampDatacubeAxis",
    },
    "engine_options": engine_options,
}


request = Request(
    ConvexPolytope(["param"], [[165]]),
    ConvexPolytope(["time"], [[pd.Timedelta(hours=1, minutes=0)], [pd.Timedelta(hours=3, minutes=0)]]),
    ConvexPolytope(["resolution"], [["high"]]),
    ConvexPolytope(["type"], [["fc"]]),
    ConvexPolytope(["model"], [["icon"]]),
    ConvexPolytope(["stream"], [["clte"]]),
    ConvexPolytope(["realization"], [[1]]),
    ConvexPolytope(["expver"], [["0001"]]),
    ConvexPolytope(["experiment"], [["cont"]]),
    ConvexPolytope(["generation"], [[2]]),
    ConvexPolytope(["levtype"], [["sfc"]]),
    ConvexPolytope(["activity"], [["baseline"]]),
    ConvexPolytope(["dataset"], [["climate-dt"]]),
    ConvexPolytope(["class"], [["d1"]]),
    ConvexPolytope(["date"], [[pd.Timestamp("19950101")]]),
    ConvexPolytope(["latitude", "longitude"], [[0, 0], [0.5, 0.5], [0, 0.5]]),
)

# print(fdb_tree.select({"param": "165", "activity": "baseline", "resolution": "high"}))

qubeddatacube = QubedDatacube(fdb_tree, datacube_axes, datacube_transformations)
slicer = QubedSlicer()
self_API = Polytope(
    datacube=fdb_tree,
    options=options,
)
time1 = time.time()
# result = self_API.retrieve(request)
result = self_API.slice(self_API.datacube, request.polytopes())
time2 = time.time()

print(result)

print("TIME EXTRACTING USING QUBED")
print(time2 - time1)

# USING NORMAL GJ


options = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "date", "transformations": [{"name": "type_change", "type": "date"}]},
        {"axis_name": "time", "transformations": [{"name": "type_change", "type": "time"}]},
        {
            "axis_name": "values",
            "transformations": [
                {"name": "mapper", "type": "healpix_nested", "resolution": 1024, "axes": ["latitude", "longitude"]}
            ],
        },
        {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
        {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
    ],
    "compressed_axes_config": [
        "longitude",
    ],
    "pre_path": {"class": "d1", "model": "ifs-nemo", "resolution": "high"},
}

fdbdatacube = gj.GribJump()
slicer = HullSlicer()


request = Request(
    ConvexPolytope(["param"], [["164"]]),
    ConvexPolytope(["time"], [[pd.Timedelta(hours=1, minutes=0)], [pd.Timedelta(hours=3, minutes=0)]]),
    ConvexPolytope(["resolution"], [["high"]]),
    ConvexPolytope(["type"], [["fc"]]),
    ConvexPolytope(["model"], [["ifs-nemo"]]),
    ConvexPolytope(["stream"], [["clte"]]),
    ConvexPolytope(["realization"], ["1"]),
    ConvexPolytope(["expver"], [["0001"]]),
    ConvexPolytope(["experiment"], [["ssp3-7.0"]]),
    ConvexPolytope(["generation"], [["1"]]),
    ConvexPolytope(["levtype"], [["sfc"]]),
    ConvexPolytope(["activity"], [["scenariomip"]]),
    ConvexPolytope(["dataset"], [["climate-dt"]]),
    ConvexPolytope(["class"], [["d1"]]),
    ConvexPolytope(["date"], [[pd.Timestamp("20220811")]]),
    ConvexPolytope(["latitude", "longitude"], [[0, 0], [0.5, 0.5], [0, 0.5]]),
)

time3 = time.time()
# result = self_API.retrieve(request)
# result = self_API.slice(request.polytopes())
time4 = time.time()

print("TIME EXTRACTING USING GJ NORMAL")
print(time4 - time3)
