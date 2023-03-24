import xarray as xr

from polytope.engine.hullslicer import HullSlicer
from polytope.datacube.xarray import XArrayDatacube
from polytope.shapes import *
from polytope.polytope import Request, Polytope

class TestSlicingEra5Data():

    def setup_method(self, method):

        array = xr.open_dataset("./tests/data/era5-levels-members.grib", engine='cfgrib')
        self.xarraydatacube = XArrayDatacube(array)
        self.slicer = HullSlicer()
        self.API = Polytope(datacube=array, engine=self.slicer)

    def test_2D_box(self):

        request = Request(
            Box(["number", "isobaricInhPa"], [3,0.0], [6,1000.0]),
            Select("time", ["2017-01-02T12:00:00"]),  # TODO: if you forget to make this a list, it treats the string as an array. Some warning would be good!
            Box(["latitude", "longitude"], lower_corner=[10.0, 0.0], upper_corner=[0.0, 30.0])
        )

        result = self.API.retrieve(request)
        result.pprint()

        assert len(result.leaves) == 4 * 1 * 2 * 4 * 11 
