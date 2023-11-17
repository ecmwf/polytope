import time

import pandas as pd

import pyfdb
import os
import tempfile
import shutil
from eccodes import codes_grib_find_nearest, codes_grib_new_from_file


class TestSlicingFDBDatacube:
    def setup_method(self, method):
        self.request = {
                        'domain': 'g',
                        'stream': 'oper',
                        'levtype': 'sfc',
                        'step': ['0', "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "29", "30", "31", "32", "33", "34", "35", "36", "37", "38", "39", "40", "41", "42", "43", "44", "45", "46", "47", "48", "49", "50", "51", "52", "53", "54", "55", "56", "57", "58", "59", "60", "61", "62", "63", "64", "65", "66", "67", "68", "69", "70", "71", "72", "73", "74", "75"],
                        #, "76", "77", "78", "79", "80", "81", "82", "83", "84", "85", "86", "87", "88", "89"],
                        'expver': '0001',
                        'date': '20231102',
                        'class': 'od',
                        'param': '167.128',
                        'time': '0000',
                        'type': 'fc',
                        "repres": "gg",
                    }
        self.fdb = pyfdb.FDB()

    def find_nearest_latlon(self, grib_file, target_lat, target_lon):
        # Open the GRIB file
        f = open(grib_file)

        # Load the GRIB messages from the file
        messages = []
        while True:
            message = codes_grib_new_from_file(f)
            if message is None:
                break
            messages.append(message)

        # Find the nearest grid points
        nearest_points = []
        for message in messages:
            nearest_index = codes_grib_find_nearest(message, target_lat, target_lon)
            nearest_points.append(nearest_index)

        # Close the GRIB file
        f.close()

        return nearest_points
    

    # Testing different shapes
    # @pytest.mark.skip(reason="can't install fdb branch on CI")
    def test_fdb_datacube(self):
        time1 = time.time()
        with open("test_fdb_read_original.grib", 'wb') as o, self.fdb.retrieve(self.request) as i:
            shutil.copyfileobj(i, o)
        self.find_nearest_latlon("test_fdb_read_original.grib", 0.035149384216, 0)
        print(time.time() - time1)
