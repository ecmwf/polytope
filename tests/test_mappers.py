from polytope.datacube.mappers import OctahedralGridMap


class TestMapper:
    def test_octahedral_mapper_init(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMap(base_axis, mapped_axes, resolution)
        assert octahedral_mapper._base_axis == base_axis
        assert octahedral_mapper._mapped_axes == mapped_axes
        assert octahedral_mapper._resolution == resolution

    def test_first_axis_vals_01280_grid(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMap(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.first_axis_vals()[:5] == [89.94618771566562, 89.87647835333229, 89.80635731954224,
                                                           89.73614327160958, 89.6658939412157]
        assert len(octahedral_mapper.first_axis_vals()) == 1280*2

    def test_first_axis_vals_other_grid(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 640
        octahedral_mapper = OctahedralGridMap(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.first_axis_vals()[:5] == [89.89239644559007, 89.75300494317403, 89.61279025859908,
                                                           89.47238958206113, 89.33191835438183]
        assert len(octahedral_mapper.first_axis_vals()) == 640*2

    def test_map_first_axis(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMap(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.map_first_axis(89.7, 89.96) == [89.94618771566562, 89.87647835333229,
                                                                 89.80635731954224, 89.73614327160958]

    def test_second_axis_vals(self):
        mapped_axes = ["lat", "lon"]
        base_axis = "base"
        resolution = 1280
        octahedral_mapper = OctahedralGridMap(base_axis, mapped_axes, resolution)
        assert octahedral_mapper.second_axis_vals(0.035149384215604956)[0] == 0
        assert octahedral_mapper.second_axis_vals(10.017574499477174)[0] == 0
        assert octahedral_mapper.second_axis_vals(89.94618771566562)[10] == 180
        assert len(octahedral_mapper.second_axis_vals(89.94618771566562)) == 20
        assert len(octahedral_mapper.second_axis_vals(89.87647835333229)) == 24
        assert len(octahedral_mapper.second_axis_vals(0.035149384215604956)) == 5136

    def test_map_second_axis(self):
        pass

    def test_axes_idx_to_octahedral_idx(self):
        pass

    def test_unmap(self):
        pass
