# (C) Copyright 2023 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import logging
import re

import numpy as np

LOG = logging.getLogger(__name__)

FULL_GLOBE = 360.0
FULL_GLOBE_EPS = 1e-8
DEGREE_EPS = 1e-8

HEALPIX_PATTERN = re.compile(r"[Hh]\d+")
RGG_PATTERN = re.compile(r"[OoNn]\d+")


# NOTE: this is a temporary code until the full gridspec
# implementation is available via earthkit-geo.


def same_coord(x, y, eps=DEGREE_EPS):
    return abs(x - y) < eps


class GridSpec(dict):
    DEFAULTS = {
        "i_scans_negatively": 0,
        "j_points_consecutive": 0,
        "j_scans_positively": 0,
    }
    DEFAULT_AREA = [90, 0, -90, 360]

    COMPARE_KEYS = {
        "type",
        "grid",
        "i_scans_negatively",
        "j_points_consecutive",
        "j_scans_positively",
    }

    def __init__(self, gs):
        self._global_ew = None
        self._global_ns = None
        super().__init__(gs)

    @staticmethod
    def _normalise(d):
        for k, v in d.items():
            if isinstance(v, tuple):
                d[k] = list(v)

    @staticmethod
    def from_dict(d):
        gs = dict(GridSpec.DEFAULTS)
        gs.update(d)
        GridSpec._normalise(gs)

        t_name, t = GridSpec._infer_spec_type(gs)
        if t is None:
            raise ValueError(f"Unsupported gridspec={d}")

        gs["type"] = t_name
        return t(gs)

    @staticmethod
    def _infer_spec_type(spec):
        spec_type = spec.get("type", None)
        if spec_type is None:
            grid = spec["grid"]
            for k, gs in GRIDSPEC_TYPES.items():
                if gs.type_match(grid):
                    return k, gs

        return spec_type, GRIDSPEC_TYPES.get(spec_type, None)

    def __eq__(self, o):
        # print(f"__eq__ self={self} o={o}")
        if self.get("type", "") != o.get("type", ""):
            return False

        for k in self.COMPARE_KEYS:
            if not self.compare_key(k, self[k], o[k]):
                return False

        if "shape" in self and "shape" in o:
            if self["shape"] != o["shape"]:
                return False
        return True

    @staticmethod
    def compare_key(key, v1, v2):
        if isinstance(v1, str) and isinstance(v2, str):
            return v1 == v2
        elif key == "grid" and isinstance(v1, list) and isinstance(v2, list):
            return np.allclose(np.array(v1), np.array(v2), atol=1e-6)
        elif isinstance(v1, list) and isinstance(v2, list):
            return v1 == v2
        elif isinstance(v1, float) and isinstance(v2, float):
            return np.isclose(v1, v2)
        elif isinstance(v1, int) and isinstance(v2, int):
            return v1 == v2
        else:
            return str(v1) == str(v2)

    @staticmethod
    def same_area(area1, area2, eps=DEGREE_EPS):
        if len(area1) == len(area2):
            return all(same_coord(v1, v2, eps=eps) for v1, v2 in zip(area1, area2))
        return False

    def has_default_area(self):
        return self.same_area(self["area"], self.DEFAULT_AREA)

    @staticmethod
    def normalise_lon(lon, minimum):
        while lon < minimum:
            lon += FULL_GLOBE
        while lon >= minimum + FULL_GLOBE:
            lon -= FULL_GLOBE
        return lon

    def is_global(self):
        return self.is_global_ew() and self.is_global_ns()

    def is_global_ew(self):
        if self._global_ew is not None:
            return self._global_ew
        else:
            raise NotADirectoryError

    def is_global_ns(self):
        if self._global_ns is not None:
            return self._global_ns
        else:
            raise NotADirectoryError


class LLGridSpec(GridSpec):
    GLOBAL_AREAS = {
        (0.1, 0.1): [90, 0, -90, 359.9],
        (0.125, 0.125): [90, 0, -90, 359.875],
        (0.15, 0.15): [90, 0, -90, 359.85],
        (0.2, 0.2): [90, 0, -90, 359.8],
        (0.25, 0.25): [90, 0, -90, 359.75],
        (0.3, 0.3): [90, 0, -90, 359.7],
        (0.4, 0.4): [90, 0, -90, 359.6],
        (0.5, 0.5): [90, 0, -90, 359.5],
        (0.6, 0.6): [90, 0, -90, 359.4],
        (0.7, 0.7): [89.6, 0, -89.6, 359.8],
        (0.75, 0.75): [90, 0, -90, 359.25],
        (0.8, 0.8): [89.6, 0, -89.6, 359.2],
        (0.9, 0.9): [90, 0, -90, 359.1],
        (1, 1): [90, 0, -90, 359],
        (1.2, 1.2): [90, 0, -90, 358.8],
        (1.25, 1.25): [90, 0, -90, 358.75],
        (1.4, 1.4): [89.6, 0, -89.6, 359.8],
        (1.5, 1.5): [90, 0, -90, 358.5],
        (1.6, 1.6): [89.6, 0, -89.6, 358.4],
        (1.8, 1.8): [90, 0, -90, 358.2],
        (2, 2): [90, 0, -90, 358],
        (2.5, 2.5): [90, 0, -90, 357.5],
        (5, 5): [90, 0, -90, 355],
        (10, 10): [90, 0, -90, 350],
    }

    def __init__(self, gs):
        super().__init__(gs)

        if "global" not in gs and "area" not in gs:
            self["global"] = 1
            self["area"] = LLGridSpec.GLOBAL_AREAS.get(
                (self["grid"][0], self["grid"][1]), self.DEFAULT_AREA
            )

        self.setdefault("area", self.DEFAULT_AREA)

        if self.get("global", 0) or self.has_default_area():
            self._global_ew = True
            self._global_ns = True

    def __eq__(self, o):
        if not super().__eq__(o):
            return False

        if self.same_area(self["area"], o["area"]):
            return True

        # sanity check: north and south must be the same
        if not same_coord(self.north, o.north) or not same_coord(self.south, o.south):
            return False

        # west-east
        if self.is_global_ew() and o.is_global_ew():
            west = self.normalise_lon(self.west, 0)
            west_o = self.normalise_lon(o.west, 0)
            if same_coord(west, west_o):
                return True

        # TODO: add code for non global grids
        return False

    @property
    def west(self):
        return self["area"][1]

    @property
    def east(self):
        return self["area"][3]

    @property
    def north(self):
        return self["area"][0]

    @property
    def south(self):
        return self["area"][2]

    @property
    def dx(self):
        return abs(self["grid"][0])

    def is_global_ew(self):
        if self._global_ew is None:
            west = self.normalise_lon(self.west, 0)
            east = self.normalise_lon(self.east, 0)
            self._global_ew = False
            if east < west:
                east += FULL_GLOBE
            if abs(east - west) < FULL_GLOBE_EPS:
                self._global_ew = True
            elif abs(east - west - FULL_GLOBE) < FULL_GLOBE_EPS:
                self._global_ew = True
            elif abs(FULL_GLOBE - (east - west) - self.dx) < FULL_GLOBE_EPS:
                self._global_ew = True
        return self._global_ew

    @staticmethod
    def type_match(grid):
        if isinstance(grid, list) and len(grid) == 2:
            return True
        return False


class ReducedGGGridSpec(GridSpec):
    def __init__(self, gs):
        super().__init__(gs)

        self.setdefault("area", self.DEFAULT_AREA)
        if self.get("global", 0) or self.has_default_area():
            self._global_ew = True
            self._global_ns = True

        self._octahedral = None
        self._N = None
        self._eps = 0.12

    def __eq__(self, o):
        if not super().__eq__(o):
            return False

        if self.same_area(self["area"], o["area"], eps=self._eps):
            return True

        # check if west the same for global grids
        if self.is_global() and o.is_global():
            west = self.normalise_lon(self.west, 0)
            west_o = self.normalise_lon(o.west, 0)
            if same_coord(west, west_o, eps=self._eps):
                return True

        # TODO: add code for non global grids
        return False

    @property
    def west(self):
        return self["area"][1]

    @property
    def east(self):
        return self["area"][3]

    @property
    def dx(self):
        if self.octahedral:
            return FULL_GLOBE / (4 * self.N + 16)
        else:
            return FULL_GLOBE / (4 * self.N)

    def is_global_ew(self):
        if self._global_ew is None:
            west = self.normalise_lon(self.west, 0)
            east = self.normalise_lon(self.east, 0)
            self._global_ew = False
            if east < west:
                east += FULL_GLOBE
            if abs(east - west) < FULL_GLOBE_EPS:
                self._global_ew = True
            elif abs(east - west - FULL_GLOBE) < FULL_GLOBE_EPS:
                self._global_ew = True
            elif abs(FULL_GLOBE - (east - west) - self.dx) < FULL_GLOBE_EPS:
                self._global_ew = True
        return self._global_ew

    def is_global_ns(self):
        if self._global_ns is None:
            self._global_ns = True
        return self._global_ns

    def _inspect_grid(self):
        if self._N is None or self._octahedral is None:
            grid = self["grid"]
            octahedral = self.get("octahedral", 0)
            if not isinstance(grid, str) or not RGG_PATTERN.match(grid):
                raise ValueError(f"Invalid {grid=}")
            try:
                if grid[0] == "N":
                    N = int(grid[1:])
                    octahedral = 0
                elif grid[0] == "O":
                    N = int(grid[1:])
                    octahedral = 1
            except Exception as e:
                raise ValueError(f"Invalid {grid=} {e}")
            if N < 1 or N > 1000000:
                raise ValueError(f"Invalid {N=}")
            self._N = N
            self._octahedral = octahedral

    @property
    def N(self):
        if self._N is None:
            self._inspect_grid()
        return self._N

    @property
    def octahedral(self):
        if self._octahedral is None:
            self._inspect_grid()
        return self._octahedral

    @staticmethod
    def type_match(grid):
        if isinstance(grid, str):
            if RGG_PATTERN.match(grid):
                return True
        return False


class HealpixGridSpec(GridSpec):
    def __init__(self, gs):
        super().__init__(gs)

        self._global_ew = True
        self._global_ns = True
        self.setdefault("area", self.DEFAULT_AREA)
        self._ordering = None
        self._N = None

    @property
    def west(self):
        return self["area"][1]

    @property
    def east(self):
        return self["area"][3]

    @property
    def dx(self):
        if self.octahedral:
            return FULL_GLOBE / (4 * self.N + 16)
        else:
            return FULL_GLOBE / (4 * self.N)

    def __eq__(self, o):
        if not super().__eq__(o):
            return False

        return self.ordering == o.ordering

    def _inspect_grid(self):
        if self._N is None or self._ordering is None:
            grid = self["grid"]
            if not self.type_match(grid):
                raise ValueError(f"Invalid healpix {grid=}")

            try:
                N = int(grid[1:])
            except Exception:
                raise ValueError(f"Invalid healpix number in {grid=}")

            ordering = self.get("ordering", "ring")
            if ordering not in ["ring", "nested"]:
                raise ValueError(f"Invalid {ordering=}, must be 'ring' or 'nested'")

            if N < 1 or N > 1000000:
                raise ValueError(f"Invalid healpix number in {grid=}")
            self._N = N
            self._ordering = ordering

    @property
    def N(self):
        if self._N is None:
            self._inspect_grid()
        return self._N

    @property
    def ordering(self):
        if self._ordering is None:
            self._inspect_grid()
        return self._ordering

    @staticmethod
    def type_match(grid):
        if isinstance(grid, str):
            return HEALPIX_PATTERN.match(grid)
        return False


GRIDSPEC_TYPES = {
    "regular_ll": LLGridSpec,
    "reduced_gg": ReducedGGGridSpec,
    "healpix": HealpixGridSpec,
}
