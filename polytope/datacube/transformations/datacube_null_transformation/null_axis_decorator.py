def null(cls):
    if cls.type_change:
        old_find_indexes = cls.find_indexes

        def find_indexes(path, datacube):
            return old_find_indexes(path, datacube)

        def find_indices_between(index_ranges, low, up, datacube, method=None):
            indexes_between_ranges = []
            for indexes in index_ranges:
                indexes_between = [i for i in indexes if low <= i <= up]
                indexes_between_ranges.append(indexes_between)
            return indexes_between_ranges

        def remap(range):
            return [range]

        cls.remap = remap
        cls.find_indexes = find_indexes
        cls.find_indices_between = find_indices_between

    return cls
