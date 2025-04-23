from polytope_feature.shapes import Box, Select, Span
from polytope_feature.polytope import Polytope, Request
from polytope_feature.engine.qubed_slicer import QubedSlicer
from polytope_feature.datacube.backends.qubed import QubedDatacube
from polytope_feature.datacube.backends.fdb import FDBDatacube
import pytest
from qubed import Qube
import requests
from polytope_feature.datacube.datacube_axis import PandasTimedeltaDatacubeAxis, PandasTimestampDatacubeAxis, UnsliceableDatacubeAxis, FloatDatacubeAxis
from polytope_feature.datacube.backends.test_qubed_slicing import actual_slice
from polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change import TypeChangeStrToTimestamp, TypeChangeStrToTimedelta
import pandas as pd
from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.healpix_nested import NestedHealpixGridMapper

from polytope_feature.shapes import ConvexPolytope
import time
import pygribjump as gj
from polytope_feature.engine.hullslicer import HullSlicer


fdb_tree = Qube.from_json(requests.get(
    "https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate_dt.json").json())


combi_polytopes = [
    ConvexPolytope(["param"], [["164"]]),
    ConvexPolytope(["time"], [[pd.Timedelta(hours=0, minutes=0)], [pd.Timedelta(hours=12, minutes=0)]]),
    ConvexPolytope(["resolution"], [["high"]]),
    ConvexPolytope(["type"], [["fc"]]),
    ConvexPolytope(["model"], [['ifs-nemo']]),
    ConvexPolytope(["stream"], [["clte"]]),
    ConvexPolytope(["realization"], ["1"]),
    ConvexPolytope(["expver"], [['0001']]),
    ConvexPolytope(["experiment"], [['ssp3-7.0']]),
    ConvexPolytope(["generation"], [["1"]]),
    ConvexPolytope(["levtype"], [["sfc"]]),
    ConvexPolytope(["activity"], [["scenariomip"]]),
    ConvexPolytope(["dataset"], [["climate-dt"]]),
    ConvexPolytope(["class"], [["d1"]]),
    ConvexPolytope(["date"], [[pd.Timestamp("20220811")], [pd.Timestamp("20220912")]]),
    ConvexPolytope(["latitude", "longitude"], [[0, 0], [0.5, 0.5], [0, 0.5]])
]

# TODO: add lat and lon axes
datacube_axes = {"param": UnsliceableDatacubeAxis(),
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
                 "latitude": FloatDatacubeAxis(),
                 "longitude": FloatDatacubeAxis()}

time_val = pd.Timedelta(hours=0, minutes=0)
date_val = pd.Timestamp("20300101T000000")


# TODO: add grid axis transformation
datacube_transformations = {
    "time": TypeChangeStrToTimedelta("time", time_val),
    "date": TypeChangeStrToTimestamp("date", date_val),
    "values": NestedHealpixGridMapper("values", ["latitude", "longitude"], 1024)
}


options = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        # {
        #     "axis_name": "date",
        #     "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        # },
        # {"axis_name": "date", "transformations": [{"name": "type_change", "type": "date"}]},
        # {"axis_name": "time", "transformations": [{"name": "type_change", "type": "time"}]},
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
    "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
}

# request = Request(
#     Select("step", [0]),
#     Select("levtype", ["sfc"]),
#     Select("date", [pd.Timestamp("20230625T120000")]),
#     Select("domain", ["g"]),
#     Select("expver", ["0001"]),
#     Select("param", ["167"]),
#     Select("class", ["od"]),
#     Select("stream", ["oper"]),
#     Select("type", ["an"]),
#     Box(["latitude", "longitude"], [0, 0], [0.2, 0.2]),
# )

request = Request(ConvexPolytope(["param"], [["164"]]),
                  ConvexPolytope(["time"], [[pd.Timedelta(hours=1, minutes=0)], [pd.Timedelta(hours=3, minutes=0)]]),
                  ConvexPolytope(["resolution"], [["high"]]),
                  ConvexPolytope(["type"], [["fc"]]),
                  ConvexPolytope(["model"], [['ifs-nemo']]),
                  ConvexPolytope(["stream"], [["clte"]]),
                  ConvexPolytope(["realization"], ["1"]),
                  ConvexPolytope(["expver"], [['0001']]),
                  ConvexPolytope(["experiment"], [['ssp3-7.0']]),
                  ConvexPolytope(["generation"], [["1"]]),
                  ConvexPolytope(["levtype"], [["sfc"]]),
                  ConvexPolytope(["activity"], [["scenariomip"]]),
                  ConvexPolytope(["dataset"], [["climate-dt"]]),
                  ConvexPolytope(["class"], [["d1"]]),
                  ConvexPolytope(["date"], [[pd.Timestamp("20220811")]]),
                  ConvexPolytope(["latitude", "longitude"], [[0, 0], [5, 5], [0, 5]]))

qubeddatacube = QubedDatacube(fdb_tree, datacube_axes, datacube_transformations)
slicer = QubedSlicer()
self_API = Polytope(
    datacube=qubeddatacube,
    engine=slicer,
    options=options,
)
time1 = time.time()
result = self_API.retrieve(request)
time2 = time.time()

print("TIME EXTRACTING USING QUBED")
print(time2 - time1)

# USING NORMAL GJ


options = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
        # {
        #     "axis_name": "date",
        #     "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
        # },
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
        # "latitude",
        # "levtype",
        # "step",
        # "date",
        # "domain",
        # "expver",
        # "param",
        # "class",
        # "stream",
        # "type",
    ],
    "pre_path": {"class": "d1", "model": "ifs-nemo", "resolution": "high"},
}

fdbdatacube = gj.GribJump()
slicer = HullSlicer()
self_API = Polytope(
    datacube=fdbdatacube,
    engine=slicer,
    options=options,
)


request = Request(ConvexPolytope(["param"], [["164"]]),
                  ConvexPolytope(["time"], [[pd.Timedelta(hours=1, minutes=0)], [pd.Timedelta(hours=3, minutes=0)]]),
                  ConvexPolytope(["resolution"], [["high"]]),
                  ConvexPolytope(["type"], [["fc"]]),
                  ConvexPolytope(["model"], [['ifs-nemo']]),
                  ConvexPolytope(["stream"], [["clte"]]),
                  ConvexPolytope(["realization"], ["1"]),
                  ConvexPolytope(["expver"], [['0001']]),
                  ConvexPolytope(["experiment"], [['ssp3-7.0']]),
                  ConvexPolytope(["generation"], [["1"]]),
                  ConvexPolytope(["levtype"], [["sfc"]]),
                  ConvexPolytope(["activity"], [["scenariomip"]]),
                  ConvexPolytope(["dataset"], [["climate-dt"]]),
                  ConvexPolytope(["class"], [["d1"]]),
                  ConvexPolytope(["date"], [[pd.Timestamp("20220811")]]),
                  ConvexPolytope(["latitude", "longitude"], [[0, 0], [5, 5], [0, 5]]))

time3 = time.time()
result = self_API.retrieve(request)
time4 = time.time()

print("TIME EXTRACTING USING GJ NORMAL")
print(time4 - time3)


# print(result)

# print(result.leaves)

# sliced_tree = actual_slice(fdb_tree, combi_polytopes, datacube_axes, datacube_transformations)
