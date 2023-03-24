import pytest
from itertools import product

from polytope import ConvexPolytope
import polytope.engine.hullslicer
from polytope.datacube.mock import MockDatacube
from polytope.utility.profiling import benchmark

class TestHullSlicer():

    def setup_method(self, method):
        self.slicer = polytope.engine.hullslicer.HullSlicer()

    def construct_nd_cube(self, dimension, lower=-1, upper=1):
        axes = [ str(chr(97+ax)) for ax in range(dimension) ]
        points = list(product([upper, lower], repeat=dimension))
        return ConvexPolytope(axes, points)

    def test_3D(self):
        p3 = self.construct_nd_cube(3)
        print(p3)
        p2 = polytope.engine.hullslicer.slice(p3, "c", 0.5)
        print(p2)
        p1 = polytope.engine.hullslicer.slice(p2, "b", 0.5)
        print(p1)

    def test_4D(self):

        p = self.construct_nd_cube(4)
        print(p)
        while len(p.axes()) > 1:
            p = polytope.engine.hullslicer.slice(p, p._axes[-1], 0.5)
            print(p)

    def test_ND(self):

        with benchmark("4D"):
            p = self.construct_nd_cube(4)
            while len(p.axes()) > 1:
                p = polytope.engine.hullslicer.slice(p, p._axes[-1], 0.5)

        with benchmark("5D"):
            p = self.construct_nd_cube(5)
            while len(p.axes()) > 1:
                p = polytope.engine.hullslicer.slice(p, p._axes[-1], 0.5)

        with benchmark("6D"):
            p = self.construct_nd_cube(6)
            while len(p.axes()) > 1:
                p = polytope.engine.hullslicer.slice(p, p._axes[-1], 0.5)

        with benchmark("7D"):
            p = self.construct_nd_cube(7)
            while len(p.axes()) > 1:
                p = polytope.engine.hullslicer.slice(p, p._axes[-1], 0.5)

        # QHull is not performant above 7D as per its documentation
        # with benchmark("8D"):
        #     p = self.construct_nd_cube(8)
        #     while len(p.axes) > 1:
        #         p = polytope.engine.hullslicer.slice(p, p.axes[-1], 0.5)

    @pytest.mark.skip(reason="This is too slow.")
    def test_extract(self):

        # TODO: This is slow in 6D, just because of the huge multiplication of polytopes (11x11x11x11x6)
        # Early prototyping shows it is not the convex hull computation which is slow,
        # but the python code for slicing/deleting axes
        self.datacube = MockDatacube( {"a" : 20, "b" : 20, "c": 20, "d": 20, "x": 10, "y":10 })
        p1 = self.construct_nd_cube(4, 0, 10)
        p2 = self.construct_nd_cube(2, 0, 5)
        p2._axes = ["x", "y"]
        self.slicer.extract(self.datacube, [p1, p2])


if __name__ == "__main__":
    t = TestHullSlicer()
    t.setup_method(None)

    import cProfile
    pr = cProfile.Profile()
    pr.enable()

    t.test_extract()

    pr.disable()
    pr.dump_stats("hull_extract.prof")
    pr.print_stats(sort="time")

    # view with `snakeviz hull_extract.prof`