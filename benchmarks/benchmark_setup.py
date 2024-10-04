from polytope.engine.hullslicer import HullSlicer
from polytope.polytope import Polytope

import pygribjump as gj


class PolytopeBenchmarkEnsembleSurface():
    def __init__(self):
        options = {
                    "axis_config": [
                        {
                            "axis_name": "date",
                            "transformations": [{"name": "merge", "other_axis": "time", "linkers": ["T", "00"]}],
                        },
                        {
                            "axis_name": "values",
                            "transformations": [
                                {
                                    "name": "mapper",
                                    "type": "octahedral",
                                    "resolution": 1280,
                                    "axes": ["latitude", "longitude"],
                                }
                            ],
                        },
                        {"axis_name": "latitude", "transformations": [{"name": "reverse", "is_reverse": True}]},
                        {"axis_name": "longitude", "transformations": [{"name": "cyclic", "range": [0, 360]}]},
                        {"axis_name": "step", "transformations": [{"name": "type_change", "type": "int"}]},
                        {"axis_name": "number", "transformations": [{"name": "type_change", "type": "int"}]},
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
                        "number"
                    ],
                    "pre_path": {"class": "od", "expver": "0079", "levtype": "sfc", "stream": "enfo", "domain": "g", "type": "pf"},
                }

        fdbdatacube = gj.GribJump()
        slicer = HullSlicer()
        self.API = Polytope(
            datacube=fdbdatacube,
            engine=slicer,
            options=options,
        )
