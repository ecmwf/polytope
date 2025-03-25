from qubed import Qube
import requests
from polytope_feature.datacube.datacube_axis import PandasTimedeltaDatacubeAxis, PandasTimestampDatacubeAxis, UnsliceableDatacubeAxis
from polytope_feature.datacube.backends.test_qubed_slicing import actual_slice
from polytope_feature.datacube.transformations.datacube_type_change.datacube_type_change import TypeChangeStrToTimestamp, TypeChangeStrToTimedelta
import pandas as pd

from polytope_feature.shapes import ConvexPolytope


fdb_tree = Qube.from_json(requests.get(
    "https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate_dt.json").json())

print(fdb_tree.axes().keys())


combi_polytopes = [
    ConvexPolytope(["param"], [["168"]]),
    ConvexPolytope(["time"], [[pd.Timedelta(hours=0, minutes=0)], [pd.Timedelta(hours=12, minutes=0)]]),
    ConvexPolytope(["resolution"], [["high"]]),
    ConvexPolytope(["type"], [["fc"]]),
    ConvexPolytope(["model"], ['ifs-nemo']),
    ConvexPolytope(["stream"], [["clte"]]),
    ConvexPolytope(["realization"], ["1"]),
    ConvexPolytope(["expver"], [['0001']]),
    ConvexPolytope(["experiment"], [['ssp3-7.0']]),
    ConvexPolytope(["generation"], [["1"]]),
    ConvexPolytope(["levtype"], [["sfc"]]),
    ConvexPolytope(["activity"], [["scenariomip"]]),
    ConvexPolytope(["dataset"], [["climate-dt"]]),
    ConvexPolytope(["class"], [["d1"]]),
    ConvexPolytope(["date"], [[pd.Timestamp("20190221")], [pd.Timestamp("20190223")]])
]

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
                 "date": PandasTimestampDatacubeAxis()}

time_val = pd.Timedelta(hours=0, minutes=0)
date_val = pd.Timestamp("20300101T000000")

datacube_transformations = {
    "time": TypeChangeStrToTimedelta("time", time_val),
    "date": TypeChangeStrToTimestamp("date", date_val)
}


sliced_tree = actual_slice(fdb_tree, combi_polytopes, datacube_axes, datacube_transformations)

print(sliced_tree)

# TODO: treat the transformations to talk to the qubed tree, maybe do it

# TODO: start iterating fdb_tree and creating a new request tree

# print(fdb_tree.)


# Select("step", [0]),
# Select("levtype", ["sfc"]),
# Select("date", [pd.Timestamp("20231102T000000")]),
# Select("domain", ["g"]),
# Select("expver", ["0001"]),
# Select("param", ["167"]),
# Select("class", ["od"]),
# Select("stream", ["oper"]),
# Select("type", ["fc"]),
# Box(["latitude", "longitude"], [0, 0], [80, 80]),
