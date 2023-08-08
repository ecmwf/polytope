import pandas as pd

from polytope.datacube.datacube_axis import (
    FloatDatacubeAxis,
    IntDatacubeAxis,
    PandasTimedeltaDatacubeAxis,
    PandasTimestampDatacubeAxis,
)


class TestAxisMappers:
    def test_int_axis(self):
        axis = IntDatacubeAxis()
        assert axis.parse(2) == 2.0
        assert axis.to_float(2) == 2.0
        assert axis.from_float(2) == 2.0
        assert axis.serialize(2) == 2
        assert axis.remap([2, 3]) == [[2, 3]]

    def test_float_axis(self):
        axis = FloatDatacubeAxis()
        assert axis.parse(2) == 2.0
        assert axis.to_float(2) == 2.0
        assert axis.from_float(2) == 2.0
        assert axis.serialize(2.0) == 2.0
        assert axis.remap([2, 3]) == [[2, 3]]

    def test_float_axis_cyclic(self):
        axis = FloatDatacubeAxis()
        axis.is_cyclic = True
        axis = axis.update_axis()
        assert axis.parse(2) == 2.0
        assert axis.to_float(2) == 2.0
        assert axis.from_float(2) == 2.0
        assert axis.serialize(2.0) == 2.0

        # Test the to_intervals function
        axis.range = [1, 3]
        assert axis.to_intervals([4, 7]) == [[4, 5], [5, 7], [7, 7]]
        # Test the cyclic_remap function
        axis.range = [0, 1]
        assert axis.remap([0, 2]) == [[-1e-12, 1.000000000001], [-1e-12, 1.000000000001]]
        axis.range = [1, 2]
        assert axis.remap([1, 3]) == [[0.999999999999, 2.000000000001], [0.999999999999, 2.000000000001]]
        axis.range = [1, 3]
        assert axis.remap([1, 4]) == [[0.999999999999, 3.000000000001], [0.999999999999, 2.000000000001]]
        axis.range = [2, 4]
        assert axis.remap([0, 5]) == [
            [1.999999999999, 4.000000000001],
            [1.999999999999, 4.000000000001],
            [1.999999999999, 3.000000000001],
        ]
        axis.range = [2.3, 4.6]
        remapped = axis.remap([0.3, 5.7])
        assert remapped == [
            [2.5999999999989996, 4.600000000001],
            [2.2999999999989997, 4.600000000001],
            [2.2999999999989997, 3.4000000000010004],
        ]

        # Test the to_cyclic_value function
        axis.range = [1, 3]
        remapped = axis.remap([0, 7])
        assert remapped == [
            [1.999999999999, 3.000000000001],
            [0.999999999999, 3.000000000001],
            [0.999999999999, 3.000000000001],
            [0.999999999999, 3.000000000001],
        ]
        remapped = axis.remap([-1, 2])
        assert remapped == [[0.999999999999, 3.000000000001], [0.999999999999, 2.000000000001]]

        # Test the cyclic_offset function
        assert axis.offset([3.05, 3.1]) == 2
        assert axis.offset([1.05, 1.1]) == 0
        assert axis.offset([-5.0, -4.95]) == -6
        assert axis.offset([5.05, 5.1]) == 4

    def test_timedelta_axis(self):
        axis = PandasTimedeltaDatacubeAxis()
        time1 = pd.Timedelta("1 days")
        time2 = pd.Timedelta("1 days 2 hours")
        assert axis.parse(time1) == pd.Timedelta("1 days 00:00:00")
        assert axis.to_float(time1) == 86400.0
        assert axis.from_float(3600) == pd.Timedelta("0 days 01:00:00")
        assert axis.serialize(time1) == "1 days 00:00:00"
        assert axis.remap([time1, time2]) == [[pd.Timedelta("1 days 00:00:00"), pd.Timedelta("1 days 02:00:00")]]

    def test_timestamp_axis(self):
        axis = PandasTimestampDatacubeAxis()
        time1 = pd.Timestamp("2017-01-01 11:00:00")
        time2 = pd.Timestamp("2017-01-01 12:00:00")
        assert axis.parse(time1) == pd.Timestamp("2017-01-01 11:00:00")
        assert axis.to_float(time1) == 1483268400.0
        assert axis.from_float(1483268400.0) == pd.Timestamp("2017-01-01 11:00:00")
        assert axis.serialize(time1) == "2017-01-01 11:00:00"
        assert axis.remap([time1, time2]) == [
            [pd.Timestamp("2017-01-01 11:00:00"), pd.Timestamp("2017-01-01 12:00:00")]
        ]
