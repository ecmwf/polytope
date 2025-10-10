import time

import pandas as pd
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


def get_fdb_tree(request):
    qube_url_start = "https://qubed.lumi.apps.dte.destination-earth.eu/api/v1/select/climate-dt/?"
    qube_url = find_relevant_subcube_from_request(request, qube_url_start)
    fdb_tree = Qube.from_json(requests.get(qube_url).json())
    return fdb_tree


# fdb_tree = Qube.from_json(
#     requests.get("https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate-dt.json").json()
# )

fdb_tree = Qube.from_json(
    requests.get("https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate-dt.json").json()
)


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


options = {
    "axis_config": [
        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "expver", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "realization", "transformations": [{"name": "type_change", "type": "int"}]},
        {"axis_name": "generation", "transformations": [{"name": "type_change", "type": "int"}]},
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
    "pre_path": {"class": "od", "expver": "0001", "levtype": "sfc", "stream": "oper"},
    "datacube_axes": {
        "param": "UnsliceableDatacubeAxis",
        "time": "PandasTimedeltaDatacubeAxis",
        "resolution": "UnsliceableDatacubeAxis",
        "type": "UnsliceableDatacubeAxis",
        "model": "UnsliceableDatacubeAxis",
        "stream": "UnsliceableDatacubeAxis",
        "realization": "IntDatacubeAxis",
        "expver": "IntDatacubeAxis",
        "experiment": "UnsliceableDatacubeAxis",
        "generation": "IntDatacubeAxis",
        "levtype": "UnsliceableDatacubeAxis",
        "activity": "UnsliceableDatacubeAxis",
        "dataset": "UnsliceableDatacubeAxis",
        "class": "UnsliceableDatacubeAxis",
        "date": "PandasTimestampDatacubeAxis",
    },
}


request = Request(
    Select("param", ["165"]),
    ConvexPolytope(["time"], [[pd.Timedelta(hours=0, minutes=0)], [pd.Timedelta(hours=3, minutes=0)]]),
    ConvexPolytope(["resolution"], [["high"]]),
    ConvexPolytope(["type"], [["fc"]]),
    Select("model", ["icon"]),
    Select("stream", ["clte"]),
    ConvexPolytope(["realization"], ["1"]),
    ConvexPolytope(["expver"], [["0001"]]),
    ConvexPolytope(["experiment"], [["ssp3-7.0"]]),
    Select("generation", [1]),
    ConvexPolytope(["levtype"], [["sfc"]]),
    Select("activity", ["scenariomip"]),
    ConvexPolytope(["dataset"], [["climate-dt"]]),
    ConvexPolytope(["class"], [["d1"]]),
    ConvexPolytope(["date"], [[pd.Timestamp("20200908")]]),
    ConvexPolytope(["latitude", "longitude"], [[0, 0], [5, 5], [0, 5]]),
)

# NOTE: this qube was deleted

path_to_qube = "../qubed/"
full_qube_path = path_to_qube + "tests/example_qubes/climate-dt_with_metadata.json"
fdb_tree = Qube.load(full_qube_path)

# fdb_tree = Qube.from_json(
#     requests.get(
#         "https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate-dt_with_metadata.json"
#     ).json()
# )

qubeddatacube = QubedDatacube(fdb_tree, datacube_axes, datacube_transformations)
slicer = QubedSlicer()
self_API = Polytope(
    datacube=fdb_tree,
    engine=slicer,
    options=options,
)
time1 = time.time()
result = self_API.retrieve(request)
time2 = time.time()


print("TIME EXTRACTING USING QUBED")
print(time2 - time1)

# # USING NORMAL GJ


# options = {
#     "axis_config": [
#         {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
#         {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
#         # {
#         #     "axis_name": "date",
#         #     "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
#         # },
#         {"axis_name": "date", "transformations": [{"name": "type_change", "type": "date"}]},
#         {"axis_name": "time", "transformations": [{"name": "type_change", "type": "time"}]},
#         {
#             "axis_name": "values",
#             "transformations": [
#                 {"name": "mapper", "type": "healpix_nested", "resolution": 1024, "axes": ["latitude", "longitude"]}
#             ],
#         },
#         {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
#         {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
#     ],
#     "compressed_axes_config": [
#         "longitude",
#         # "latitude",
#         # "levtype",
#         # "step",
#         # "date",
#         # "domain",
#         # "expver",
#         # "param",
#         # "class",
#         # "stream",
#         # "type",
#     ],
#     "pre_path": {"class": "d1", "model": "ifs-nemo", "resolution": "high"},
# }

# fdbdatacube = gj.GribJump()
# slicer = HullSlicer()
# self_API = Polytope(
#     datacube=fdbdatacube,
#     engine=slicer,
#     options=options,
# )


# request = Request(ConvexPolytope(["param"], [["164"]]),
#                   ConvexPolytope(["time"], [[pd.Timedelta(hours=1, minutes=0)], [pd.Timedelta(hours=3, minutes=0)]]),
#                   ConvexPolytope(["resolution"], [["high"]]),
#                   ConvexPolytope(["type"], [["fc"]]),
#                   ConvexPolytope(["model"], [['ifs-nemo']]),
#                   ConvexPolytope(["stream"], [["clte"]]),
#                   ConvexPolytope(["realization"], ["1"]),
#                   ConvexPolytope(["expver"], [['0001']]),
#                   ConvexPolytope(["experiment"], [['ssp3-7.0']]),
#                   ConvexPolytope(["generation"], [["1"]]),
#                   ConvexPolytope(["levtype"], [["sfc"]]),
#                   ConvexPolytope(["activity"], [["scenariomip"]]),
#                   ConvexPolytope(["dataset"], [["climate-dt"]]),
#                   ConvexPolytope(["class"], [["d1"]]),
#                   ConvexPolytope(["date"], [[pd.Timestamp("20220811")]]),
#                   ConvexPolytope(["latitude", "longitude"], [[0, 0], [5, 5], [0, 5]]))

# time3 = time.time()
# result = self_API.retrieve(request)
# time4 = time.time()

# print("TIME EXTRACTING USING GJ NORMAL")
# print(time4 - time3)
