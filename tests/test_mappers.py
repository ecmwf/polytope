from polytope_feature.datacube.transformations.datacube_mappers.mapper_types.octahedral import (
    OctahedralGridMapper,
)


class TestMapper:
    def test_octahedral_mapper_init(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper._base_axis == base_axis
        assert octahedral_mapper._mapped_axes == mapped_axes
        assert octahedral_mapper._resolution == resolution

    def test_first_axis_vals_01280_grid(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.first_axis_vals()[:5] == [
            89.94618771566562,
            89.87647835333229,
            89.80635731954224,
            89.73614327160958,
            89.6658939412157,
        ]
        assert len(octahedral_mapper.first_axis_vals()) == 1280 * 2

    def test_first_axis_vals_other_grid(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 640
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.first_axis_vals()[:5] == [
            89.89239644559007,
            89.75300494317403,
            89.61279025859908,
            89.47238958206113,
            89.33191835438183,
        ]
        assert len(octahedral_mapper.first_axis_vals()) == 640 * 2

    def test_map_first_axis(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.map_first_axis(89.7, 89.96) == [
            89.94618771566562,
            89.87647835333229,
            89.80635731954224,
            89.73614327160958,
        ]

    def test_second_axis_vals(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.second_axis_vals((0.035149384215604956,))[0] == 0
        assert octahedral_mapper.second_axis_vals((10.017574499477174,))[0] == 0
        assert octahedral_mapper.second_axis_vals((89.94618771566562,))[10] == 180
        assert len(octahedral_mapper.second_axis_vals((89.94618771566562,))) == 20
        assert len(octahedral_mapper.second_axis_vals((89.87647835333229,))) == 24
        assert len(octahedral_mapper.second_axis_vals((0.035149384215604956,))) == 5136

    def test_map_second_axis(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.map_second_axis((89.94618771566562,), 0, 90) == [0, 18, 36, 54, 72, 90]

    def test_axes_idx_to_octahedral_idx(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1, 0) == 0
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1, 1) == 1
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1, 16) == 16
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1, 17) == 17
        assert octahedral_mapper.axes_idx_to_octahedral_idx(2, 0) == 20
        assert octahedral_mapper.axes_idx_to_octahedral_idx(3, 0) == 44
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1279, 0) == 3299840 - 5136 - 5136 + 4
        # at lat line 1280, we start the 1280th line, which has 5136 points
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1280, 0) == 3299840 - 5136
        # the 1281th lat line also has 5136 points, and we are exactly at the half of the number of points in the grid
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1281, 0) == 3299840
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1281, 12) == 3299852
        # the 1281th lat line has 5136 points, so when we start the 1282nd lat line, we are at the half of the grid
        # points + 5136
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1282, 0) == 3299840 + 5136
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1283, 0) == 3299840 + 5136 + 5136 - 4
        assert octahedral_mapper.axes_idx_to_octahedral_idx(1284, 0) == 3299840 + 5136 + 5136 - 4 + 5136 - 8
        # at the last lat line, we only have 20 points left in the grid
        assert octahedral_mapper.axes_idx_to_octahedral_idx(2560, 0) == 3299840 * 2 - 20

    def test_unmap(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMapper(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.unmap((89.94618771566562,), (0,))[0] == 0
        assert octahedral_mapper.unmap((0.035149384215604956,), (0,))[0] == 3299840 - 5136
        assert octahedral_mapper.unmap((-0.035149384215604956,), (0,))[0] == 3299840
