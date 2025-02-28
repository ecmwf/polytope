from qubed import Qube
import requests
from polytope_feature.datacube.datacube_axis import PandasTimedeltaDatacubeAxis, PandasTimestampDatacubeAxis, UnsliceableDatacubeAxis

from polytope_feature.shapes import ConvexPolytope


fdb_tree = Qube.from_json(requests.get(
    "https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate_dt.json").json())

print(fdb_tree.axes().keys())


combi_polytopes = [
    ConvexPolytope(["param"], [["168"]]),
    ConvexPolytope(["time"], [["0000"], ["1200"]]),
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
    ConvexPolytope(["date"], [["20190221", "20190223"]])
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
