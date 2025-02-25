from qubed import Qube
import requests

from ...shapes import ConvexPolytope


fdb_tree = Qube.from_json(requests.get(
    "https://github.com/ecmwf/qubed/raw/refs/heads/main/tests/example_qubes/climate_dt.json").json())

fdb_tree.print()
combi_polytopes = [
    # ConvexPolytope()
]

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
