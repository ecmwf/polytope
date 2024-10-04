import pandas as pd

from polytope.polytope import Request
from polytope.shapes import Span, Select, Box

from .benchmark_setup import PolytopeBenchmarkEnsembleSurface


benchmark = PolytopeBenchmarkEnsembleSurface()

request = Request(
    Span("step", 0, 360),
    Select("domain", ["g"]),
    Select("class", ["od"]),
    Select("levtype", ["sfc"]),
    Select("date", [pd.Timestamp("20240925T000000")]),
    Select("expver", ["0079"]),
    Select("param", ["164", "167", "169"]),
    Select("stream", ["enfo"]),
    Select("type", ["pf"]),
    Span("number", 1, 50),
    Box(["latitude", "longitude"], [0, 0], [10, 10])
)

result = benchmark.API.retrieve(request)
result.pprint()
