import pytest

from polytope_feature.engine.hullslicer import HullSlicer
from polytope_feature.polytope import Polytope
from polytope_feature.utility.exceptions import BadRequestError

# import geopandas as gpd
# import matplotlib.pyplot as plt


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        # Create a dataarray with 3 labelled axes using different index types
        self.options = {
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
            ],
            "pre_path": {
                "class": "od",
                "expver": "0001",
                "levtype": "sfc",
                "stream": "oper",
                "date": "20230621T120000",
            },
        }

    # Testing different shapes
    @pytest.mark.fdb
    def test_fdb_datacube(self):
        import pygribjump as gj

        with pytest.raises(BadRequestError):
            self.fdbdatacube = gj.GribJump()
            self.slicer = HullSlicer()
            self.API = Polytope(
                datacube=self.fdbdatacube,
                engine=self.slicer,
                options=self.options,
            )
