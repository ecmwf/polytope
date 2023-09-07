import copy
import math
from abc import ABC, abstractmethod
from typing import List

import tripy

"""
Shapes used for the constructive geometry API of Polytope
"""


class Shape(ABC):
    """Represents a multi-axis shape to be expanded"""

    @abstractmethod
    def polytope(self):
        raise NotImplementedError()

    @abstractmethod
    def axes(self) -> List[str]:
        raise NotImplementedError()


class ConvexPolytope(Shape):
    def __init__(self, axes, points, method=None):
        self._axes = list(axes)
        self.points = points
        self.method = method

    def extents(self, axis):
        slice_axis_idx = self.axes().index(axis)
        axis_values = [point[slice_axis_idx] for point in self.points]
        lower = min(axis_values)
        upper = max(axis_values)
        return (lower, upper)

    def __str__(self):
        return f"Polytope in {self.axes} with points {self.points}"

    def axes(self):
        return self._axes

    def polytope(self):
        return [self]


# This is the only shape which can slice on axes without a discretizer or interpolator
class Select(Shape):
    """Matches several discrete value"""

    def __init__(self, axis, values, method=None):
        self.axis = axis
        self.values = values
        self.method = method

    def axes(self):
        return [self.axis]

    def polytope(self):
        return [ConvexPolytope([self.axis], [[v]], self.method) for v in self.values]


class Span(Shape):
    """1-D range along a single axis"""

    def __init__(self, axis, lower=None, upper=None):
        assert not isinstance(lower, list)
        assert not isinstance(upper, list)
        self.axis = axis
        self.lower = lower
        self.upper = upper

    def axes(self):
        return [self.axis]

    def polytope(self):
        return [ConvexPolytope([self.axis], [[self.lower], [self.upper]])]


class All(Span):
    """Matches all indices in an axis"""

    def __init__(self, axis):
        super().__init__(axis)


class Box(Shape):
    """N-D axis-aligned bounding box (AABB), specified by two opposite corners"""

    def __init__(self, axes, lower_corner=None, upper_corner=None):
        dimension = len(axes)
        self._axes = axes
        assert len(lower_corner) == dimension
        assert len(upper_corner) == dimension

        if lower_corner is None:
            lower_corner = [-math.inf] * dimension
        if upper_corner is None:
            upper_corner = [math.inf] * dimension

        # Build every vertex of the box from the two extremes
        # ... take a binary representation of hypercube vertices
        # ... [00, 01, 10, 11] in 2D
        # ... take lower/upper corner for each 0/1
        self.vertices = []
        for i in range(0, 2**dimension):
            vertex = copy.copy(lower_corner)
            for d in range(0, dimension):
                if i >> d & 1:
                    vertex[d] = upper_corner[d]
            self.vertices.append(vertex)

        assert lower_corner in self.vertices
        assert upper_corner in self.vertices
        assert len(self.vertices) == 2**dimension

    def axes(self):
        return self._axes

    def polytope(self):
        return [ConvexPolytope(self.axes(), self.vertices)]


class Disk(Shape):
    """2-D shape bounded by an ellipse"""

    # NB radius is two dimensional
    # NB number of segments is hard-coded, not exposed to user

    def __init__(self, axes, centre=[0, 0], radius=[1, 1]):
        self._axes = axes
        self.centre = centre
        self.radius = radius
        self.segments = 12

        assert len(axes) == 2
        assert len(centre) == 2
        assert len(radius) == 2

        expanded_radius = self._expansion_to_circumscribe_circle(self.segments)
        self.points = self._points_on_circle(self.segments, expanded_radius)

        for i in range(0, len(self.points)):
            x = centre[0] + self.points[i][0] * radius[0]
            y = centre[1] + self.points[i][1] * radius[1]
            self.points[i] = [x, y]

    def _points_on_circle(self, n, r):
        return [[math.cos(2 * math.pi / n * x) * r, math.sin(2 * math.pi / n * x) * r] for x in range(0, n)]

    def _expansion_to_circumscribe_circle(self, n):
        half_angle_between_segments = math.pi / n
        return 1 / math.cos(half_angle_between_segments)

    def axes(self):
        return self._axes

    def polytope(self):
        return [ConvexPolytope(self.axes(), self.points)]


class Ellipsoid(Shape):
    # Here we use the formula for the inscribed circle in an icosahedron
    # See https://en.wikipedia.org/wiki/Platonic_solid

    def __init__(self, axes, centre=[0, 0, 0], radius=[1, 1, 1]):
        self._axes = axes
        self.centre = centre
        self.radius = radius

        assert len(axes) == 3
        assert len(centre) == 3
        assert len(radius) == 3

        expanded_radius = self._icosahedron_edge_length_coeff()
        self.points = self._points_on_icosahedron(expanded_radius)

        for i in range(0, len(self.points)):
            x = centre[0] + self.points[i][0] * radius[0]
            y = centre[1] + self.points[i][1] * radius[1]
            z = centre[2] + self.points[i][2] * radius[2]
            self.points[i] = [x, y, z]

    def axes(self):
        return self._axes

    def _points_on_icosahedron(self, coeff):
        golden_ratio = (1 + math.sqrt(5)) / 2
        return [
            [0, coeff / 2, coeff * golden_ratio / 2],
            [0, coeff / 2, -coeff * golden_ratio / 2],
            [0, -coeff / 2, coeff * golden_ratio / 2],
            [0, -coeff / 2, -coeff * golden_ratio / 2],
            [coeff / 2, coeff * golden_ratio / 2, 0],
            [coeff / 2, -coeff * golden_ratio / 2, 0],
            [-coeff / 2, coeff * golden_ratio / 2, 0],
            [-coeff / 2, -coeff * golden_ratio / 2, 0],
            [coeff * golden_ratio / 2, 0, coeff / 2],
            [coeff * golden_ratio / 2, 0, -coeff / 2],
            [-coeff * golden_ratio / 2, 0, coeff / 2],
            [-coeff * golden_ratio / 2, 0, -coeff / 2],
        ]

    def _icosahedron_edge_length_coeff(self):
        # theta is the dihedral angle for an icosahedron here
        theta = (138.19 / 180) * math.pi
        edge_length = (2 / math.tan(theta / 2)) * math.tan(math.pi / 3)
        return edge_length

    def polytope(self):
        return [ConvexPolytope(self.axes(), self.points)]


class PathSegment(Shape):
    """N-D polytope defined by a shape which is swept along a straight line between two points"""

    def __init__(self, axes, shape: Shape, start: List, end: List):
        self._axes = axes

        assert shape.axes() == self.axes()
        assert len(start) == len(self.axes())
        assert len(end) == len(self.axes())

        self.polytopes = []
        for polytope in shape.polytope():
            # We can generate a polytope by taking all the start points and all the end points and passing them
            # to the polytope constructor as-is. This is not a convex hull, there will inevitably be interior points.
            # This is currently OK, because we first determine the min/max on each axis before slicing.

            points = []
            for p in polytope.points:
                points.append([a + b for a, b in zip(p, start)])
                points.append([a + b for a, b in zip(p, end)])
            self.polytopes.append(ConvexPolytope(self.axes(), points))

    def axes(self):
        return self._axes

    def polytope(self):
        return self.polytopes


class Path(Shape):
    """N-D polytope defined by a shape which is swept along a polyline defined by multiple points"""

    def __init__(self, axes, shape, *points, closed=False):
        self._axes = axes

        assert shape.axes() == self.axes()
        for p in points:
            assert len(p) == len(self.axes())

        path_segments = []

        for i in range(0, len(points) - 1):
            path_segments.append(PathSegment(axes, shape, points[i], points[i + 1]))

        if closed:
            path_segments.append(PathSegment(axes, shape, points[-1], points[0]))

        self.union = Union(self.axes(), *path_segments)

    def axes(self):
        return self._axes

    def polytope(self):
        return self.union.polytope()


class Union(Shape):
    """N-D union of two shapes with the same axes"""

    def __init__(self, axes, *shapes):
        self._axes = axes
        for s in shapes:
            assert s.axes() == self.axes()

        self.polytopes = []

        for s in shapes:
            self.polytopes.extend(s.polytope())

    def axes(self):
        return self._axes

    def polytope(self):
        return self.polytopes


class Polygon(Shape):
    """2-D polygon defined by a set of exterior points"""

    def __init__(self, axes, points):
        self._axes = axes
        assert len(axes) == 2
        for p in points:
            assert len(p) == 2

        triangles = tripy.earclip(points)
        self.polytopes = []

        if len(points) > 0 and len(triangles) == 0:
            self.polytopes = [ConvexPolytope(self.axes(), points)]

        else:
            for t in triangles:
                tri_points = [list(point) for point in t]
                self.polytopes.append(ConvexPolytope(self.axes(), tri_points))

    def axes(self):
        return self._axes

    def polytope(self):
        return self.polytopes
