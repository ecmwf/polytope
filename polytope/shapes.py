import copy
import math
from abc import ABC, abstractmethod
from typing import List
import matplotlib.path as mpltPath

import tripy
import scipy.spatial
import numpy as np

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
    def __init__(self, axes, points, method=None, is_orthogonal=False):
        self._axes = list(axes)
        self.is_flat = False
        if len(self._axes) == 1:
            self.is_flat = True
        self.points = points
        self.method = method
        self.is_orthogonal = is_orthogonal
        self.is_in_union = False

    def add_to_union(self):
        self.is_in_union = True

    def extents(self, axis):
        if self.is_flat:
            slice_axis_idx = 0
            lower = min(self.points)[0]
            upper = max(self.points)[0]
        else:
            slice_axis_idx = self.axes().index(axis)
            axis_values = [point[slice_axis_idx] for point in self.points]
            lower = min(axis_values)
            upper = max(axis_values)
        return (lower, upper, slice_axis_idx)

    def __str__(self):
        return f"Polytope in {self.axes()} with points {self.points}"

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
        return [ConvexPolytope([self.axis], [[v]], self.method, is_orthogonal=True) for v in self.values]

    def __repr__(self):
        return f"Select in {self.axis} with points {self.values}"


class Point(Shape):
    """Matches several discrete value"""

    def __init__(self, axes, values, method=None):
        self._axes = axes
        self.values = values
        self.method = method
        self.polytopes = []
        if method == "nearest":
            assert len(self.values) == 1
        for i in range(len(axes)):
            polytope_points = [v[i] for v in self.values]
            self.polytopes.extend(
                [ConvexPolytope([axes[i]], [[point]], self.method, is_orthogonal=True) for point in polytope_points]
            )

    def axes(self):
        return self._axes

    def polytope(self):
        return self.polytopes

    def __repr__(self):
        return f"Point in {self._axes} with points {self.values}"


class Span(Shape):
    """1-D range along a single axis"""

    def __init__(self, axis, lower=-math.inf, upper=math.inf):
        assert not isinstance(lower, list)
        assert not isinstance(upper, list)
        self.axis = axis
        self.lower = lower
        self.upper = upper

    def axes(self):
        return [self.axis]

    def polytope(self):
        return [ConvexPolytope([self.axis], [[self.lower], [self.upper]], is_orthogonal=True)]

    def __repr__(self):
        return f"Span in {self.axis} with range from {self.lower} to {self.upper}"


class All(Span):
    """Matches all indices in an axis"""

    def __init__(self, axis):
        super().__init__(axis)

    def __repr__(self):
        return f"All in {self.axis}"


class Box(Shape):
    """N-D axis-aligned bounding box (AABB), specified by two opposite corners"""

    def __init__(self, axes, lower_corner=None, upper_corner=None):
        dimension = len(axes)
        self._lower_corner = lower_corner
        self._upper_corner = upper_corner
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
        return [ConvexPolytope(self.axes(), self.vertices, is_orthogonal=True)]

    def __repr__(self):
        return f"Box in {self._axes} with with lower corner {self._lower_corner} and upper corner{self._upper_corner}"


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

    def __repr__(self):
        return f"Disk in {self._axes} with centred at {self.centre} and with radius {self.radius}"


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

    def __repr__(self):
        return f"Ellipsoid in {self._axes} with centred at {self.centre} and with radius {self.radius}"


class PathSegment(Shape):
    """N-D polytope defined by a shape which is swept along a straight line between two points"""

    def __init__(self, axes, shape: Shape, start: List, end: List):
        self._axes = axes
        self._start = start
        self._end = end
        self._shape = shape

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
            poly = ConvexPolytope(self.axes(), points)
            poly.add_to_union()
            self.polytopes.append(poly)

    def axes(self):
        return self._axes

    def polytope(self):
        return self.polytopes

    def __repr__(self):
        return f"PathSegment in {self._axes} obtained by sweeping a {self._shape.__repr__()} \
            between the points {self._start} and {self._end}"


class Path(Shape):
    """N-D polytope defined by a shape which is swept along a polyline defined by multiple points"""

    def __init__(self, axes, shape, *points, closed=False):
        self._axes = axes
        self._shape = shape
        self._points = points

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

    def __repr__(self):
        return f"Path in {self._axes} obtained by sweeping a {self._shape.__repr__()} \
            between the points {self._points}"


class Union(Shape):
    """N-D union of two shapes with the same axes"""

    def __init__(self, axes, *shapes):
        self._axes = axes
        for s in shapes:
            assert s.axes() == self.axes()

        self.polytopes = []
        self._shapes = shapes

        for s in shapes:
            for poly in s.polytope():
                poly.add_to_union()
                self.polytopes.append(poly)

    def axes(self):
        return self._axes

    def polytope(self):
        return self.polytopes

    def __repr__(self):
        return f"Union in {self._axes} of the shapes {self._shapes}"


class Polygon(Shape):
    """2-D polygon defined by a set of exterior points"""

    def __init__(self, axes, points):
        self._axes = axes
        assert len(axes) == 2
        for p in points:
            assert len(p) == 2

        # TODO: if there are too many points which would slow down slicing too much, approximate the polygon shape with
        # fewer vertices
        # self._points = points
        self._points = []

        if len(points) <= 3*10e2:
            self._points = points
        else:
            tol = 1e-3  # NOTE: 1e-2 should be sufficient for most grids
            self.reduce_polygon(points, tol)
        # triangles = tripy.earclip(points)
        # self.polytopes = []

        # if len(points) > 0 and len(triangles) == 0:
        #     self.polytopes = [ConvexPolytope(self.axes(), points)]

        # else:
        #     for t in triangles:
        #         tri_points = [list(point) for point in t]
        #         poly = ConvexPolytope(self.axes(), tri_points)
        #         poly.add_to_union()
        #         self.polytopes.append(poly)

    def axes(self):
        return self._axes

    def polytope(self):
        # return self.polytopes
        triangles = tripy.earclip(self._points)
        self.polytopes = []

        if len(self._points) > 0 and len(triangles) == 0:
            self.polytopes = [ConvexPolytope(self.axes(), self._points)]

        else:
            for t in triangles:
                tri_points = [list(point) for point in t]
                poly = ConvexPolytope(self.axes(), tri_points)
                poly.add_to_union()
                self.polytopes.append(poly)
        return self.polytopes

    def __repr__(self):
        return f"Polygon in {self._axes} with points {self._points}"

    def reduce_polygon(self, points, epsilon):
        # Implement Douglas-Peucker algorithm
        k = 2  # number of polylines we divide the polygon into
        # First need to break down polygon into two polylines
        n = int(len(points)/k)
        # poly1_points = points[:n]
        sub_polys = [points[:n]]
        for i in range(k-2):
            sub_polys.append(points[n*(i+1): n*(i+2)])
        sub_polys.append(points[n*(k-1):])
        # poly2_points = points[n:]

        # Douglas-Peucker on each polyline
        # red_points_poly1 = self.douglas_peucker_algo(poly1_points, epsilon)
        # red_points_poly2 = self.douglas_peucker_algo(poly2_points, epsilon)
        reduced_points = []

        for i, poly in enumerate(sub_polys):
            # sub_poly_inside_poly = mpltPath.Path(points).contains_path(mpltPath.Path([poly[0], poly[-1]]))
            # print("HERE LOOK")
            # print(sub_poly_inside_poly)
            # if i == 1:
            #     poly = poly[2*int(len(poly)/3)+550:2*int(len(poly)/3)+800]
            reduced_points.extend(self.douglas_peucker_algo(poly, epsilon, points))
        # reduced_points = red_points_poly1
        # reduced_points.extend(red_points_poly2)
        # reduced_points_hull = self.do_convex_hull(reduced_points)
        reduced_points_hull = reduced_points
        self._points = reduced_points_hull

    def find_max_dist(self, points):
        index = 0
        dists = []
        max_dist = 0
        line_points = [points[0], points[len(points)-1]]

        for i in range(1, len(points)-1):
            point = points[i]
            dist = self.perp_dist(point, line_points)
            dists.append(dist)
            if dist > max_dist:
                max_dist = dist
                index = i

        return (max_dist, dists, index)
    
    def variation_douglas_peucker_algo(self, points, epsilon):
        # TODO: what if when the tolerance is small, we take the convex hull of the two semi-triangles points[0], p[1:index], p[index] and p[index], p[index+1:-1], p[-1]
        # Note that this could remove p[0], p[index] and p[-1] so need to ensure that we keep those
        results = []

        # find point with largest distance to line between first and last point of polyline
        if len(points) < 4:
            results = points
            return results
        
        max_dist, dists, index = self.find_max_dist(points)
        line_points = [points[0], points[len(points)-1]]

        if max(dists) == 0:
            results = line_points
            return results

        if max_dist > epsilon:
            # this means that we need to keep the max dist point in the polyline
            # and so we then need to recurse
            sub_polyline1_points = points[: index + 1]  # NOTE we include the max dist point
            sub_polyline2_points = points[index :]  # NOTE: we include the max dist point
            red_sub_polyline1 = self.variation_douglas_peucker_algo(sub_polyline1_points, epsilon)
            red_sub_polyline2 = self.variation_douglas_peucker_algo(sub_polyline2_points, epsilon)
            # results.extend(red_sub_polyline1)
            # results.extend(red_sub_polyline2)
            self.extend_without_duplicates(results, red_sub_polyline1)
            self.extend_without_duplicates(results, red_sub_polyline2)
        else:
            # left_hull = self.do_convex_hull(points[:index+1])
            # right_hull = self.do_convex_hull(points[index:])
            hull = self.do_convex_hull(points)
            results.extend(hull)
            # self.extend_without_duplicates(results, left_hull)
            # self.extend_without_duplicates(results, right_hull)
            # results.extend(left_hull)
            # results.extend(right_hull)
            # self.extend_without_duplicates(results, hull)
            # self.extend_without_duplicates(results, [points[0], points[-1]])
        return results

    def do_convex_hull(self, intersects):
        # intersects.append(intersects[0])
        try:
            hull = scipy.spatial.ConvexHull(intersects)
            vertices = hull.vertices

        except scipy.spatial.qhull.QhullError as e:
            if "less than" or "flat" in str(e):
                return intersects
        # return_points = [intersects[0]]
        return_points = []
        vertices.sort()
        return_points.extend([intersects[i] for i in vertices])
        # print(vertices)
        # print(return_points)
        # if len(intersects) - 1 not in vertices:
        #     return_points.append([intersects[-1]])
        # return [intersects[i] for i in vertices]
        return return_points
    

    def area_polygon(self, points):
        # Use Green's theorem, see
        # https://stackoverflow.com/questions/256222/which-exception-should-i-raise-on-bad-illegal-argument-combinations-in-python
        return 0.5 * abs(sum(x0*y1 - x1*y0
                            for ((x0, y0), (x1, y1)) in self.segments(points)))


    def segments(self, points):
        return zip(points, points[1:] + [points[0]])

    def douglas_peucker_algo(self, points, epsilon, original_poly):
        results = []

        # print(len(points))
        if len(points) < 3:
            results = points
            return results

        # find point with largest distance to line between first and last point of polyline
        max_dist, dists, index = self.find_max_dist(points)
        line_points = [points[0], points[len(points)-1]]

        if max(dists) == 0:
            results = line_points
            return results

        # print("NOW")
        # print(index)
        # print(len(points) -1)

        # triangle_base_polygon = [points[0], points[index], points[-1]]

        # points1_are_not_removable = []
        # points2_are_not_removable = []
        # for i in range(1, index+1):
        #     points2_are_not_removable.append(bool(True - mpltPath.Path(triangle_base_polygon).contains_point(points[i])))
        # for i in range(index+1, len(points)-1):
        #     points2_are_not_removable.append(bool(True - mpltPath.Path(triangle_base_polygon).contains_point(points[i])))
        # This is negative when we can remove points[index], otherwise we need to keep the point
        # can remove point if the line_midpoint is outside of the polygon

        # point_is_removable = []
        # point_is_removable_idx = list(range(1, index))
        # point_is_removable_idx.extend(list(range(index+1, len(points)-1)))
        # for i in range(1, index):
        #     point_is_removable.append(mpltPath.Path(triangle_base_polygon).contains_point(points[i]))
        # for i in range(index+1, len(points)-1):
        #     point_is_removable.append(mpltPath.Path(triangle_base_polygon).contains_point(points[i]))

        # if len(point_is_removable) == 0:
        #     need_to_iterate = False
        # elif all(point_is_removable):
        #     need_to_iterate = False
        # else:
        #     need_to_iterate = True
        
        # TODO: find the point that is not removable that is furthest away from line, note can use dists
        # point_is_removable.index()
        # if max_dist > epsilon or need_to_iterate:
        if max_dist > epsilon:
            # TODO: IDEA: Could compare the area of the bit we would be removing here to only iterate if we'd remove a big area?
            # NEED NOT KEEP ENTIRE TOPOLOGY? BUT HOW DO WE KNOW WHEN THERE'S AN ARM COMING INTO THE POLYGON?
            # OR JUST DO SOMETHING LIKE BELOW AFTER ITERATION WHERE WE LOOK WHETHER POINTS CAN BE REMOVED AND THEN ALSO LOOK AT AREA WHICH WOULD BE REMOVED?
            sub_polyline1_points = points[: index + 1]  # NOTE we include the max dist point
            sub_polyline2_points = points[index :]  # NOTE: we include the max dist point
            red_sub_polyline1 = self.douglas_peucker_algo(sub_polyline1_points, epsilon, original_poly)
            red_sub_polyline2 = self.douglas_peucker_algo(sub_polyline2_points, epsilon, original_poly)
            # results.extend(red_sub_polyline1)
            # results.extend(red_sub_polyline2)
            self.extend_without_duplicates(results, red_sub_polyline1)
            self.extend_without_duplicates(results, red_sub_polyline2)
            # removed_area = self.area_polygon(points)
            # poly_area = self.area_polygon(original_poly)
            # if removed_area < 0.0001 * poly_area:
            #     projected_points = [self.projected_point(points[i], [points[0], points[-1]]) for i in range(len(points))]
            #     projected_points_inside_polygon = mpltPath.Path(original_poly).contains_points(projected_points)
            
            #     if not any(projected_points_inside_polygon):
            #         results = [points[0], points[-1]]
            #     else:
            #         sub_polyline1_points = points[: index + 1]  # NOTE we include the max dist point
            #         sub_polyline2_points = points[index :]  # NOTE: we include the max dist point
            #         red_sub_polyline1 = self.douglas_peucker_algo(sub_polyline1_points, epsilon, original_poly)
            #         red_sub_polyline2 = self.douglas_peucker_algo(sub_polyline2_points, epsilon, original_poly)
            #         # results.extend(red_sub_polyline1)
            #         # results.extend(red_sub_polyline2)
            #         self.extend_without_duplicates(results, red_sub_polyline1)
            #         self.extend_without_duplicates(results, red_sub_polyline2)
            # else:
            #     # this means that we need to keep the max dist point in the polyline
            #     # and so we then need to recurse
                
            #     sub_polyline1_points = points[: index + 1]  # NOTE we include the max dist point
            #     sub_polyline2_points = points[index :]  # NOTE: we include the max dist point
            #     red_sub_polyline1 = self.douglas_peucker_algo(sub_polyline1_points, epsilon, original_poly)
            #     red_sub_polyline2 = self.douglas_peucker_algo(sub_polyline2_points, epsilon, original_poly)
            #     # results.extend(red_sub_polyline1)
            #     # results.extend(red_sub_polyline2)
            #     self.extend_without_duplicates(results, red_sub_polyline1)
            #     self.extend_without_duplicates(results, red_sub_polyline2)
        else:
            projected_points = [self.projected_point(points[i], [points[0], points[-1]]) for i in range(len(points))]
            # projected_points_inside_polygon = [mpltPath.Path(original_poly).contains_point(projected_points[i]) for i in range(len(points))]
            projected_points_inside_polygon = mpltPath.Path(original_poly).contains_points(projected_points)
            if all(projected_points_inside_polygon[1:-1]):
                # print(projected_points_inside_polygon)
                results = points
                # results = [points[0], points[-1]]
            elif not any(projected_points_inside_polygon[1:-1]):
                # TODO: why in the corner, does it not find that the projected point is inside the polygon?
                # print(projected_points_inside_polygon)
                # print(points)
                # print([points[0], points[-1]])
                # print(projected_points)
                results = [points[0], points[-1]]
                # print(results)
                # results = points
            else:
                sub_polyline1_points = points[: index + 1]  # NOTE we include the max dist point
                sub_polyline2_points = points[index :]  # NOTE: we include the max dist point
                red_sub_polyline1 = self.douglas_peucker_algo(sub_polyline1_points, epsilon, original_poly)
                red_sub_polyline2 = self.douglas_peucker_algo(sub_polyline2_points, epsilon, original_poly)
                # results.extend(red_sub_polyline1)
                # results.extend(red_sub_polyline2)
                self.extend_without_duplicates(results, red_sub_polyline1)
                self.extend_without_duplicates(results, red_sub_polyline2)
                # results = points
                # i = 0
                # while i < len(points):
                #     if projected_points_inside_polygon[i]:
                #         results.append(points[i])
                #         i += 1
                #     else:
                #         start_point = i
                #         results.append(points[start_point])
                #         while not projected_points_inside_polygon[i]:
                #             i += 1
                #             # results.append(points[i])
                #             if i == len(projected_points_inside_polygon):
                #                 results.append(points[-1])
                #                 break
                        # results.append(points[start_point])
            # new_point = self.find_new_p1(points[-1], points[0], points[1:-1], points2_are_not_removable, [0,0])
            # max_dist, dists, index = self.find_max_dist([points[0], new_point, points[-1]])
            # if dists[0]>0.1:
            #     self.extend_without_duplicates(results, points)
            # else:
            #     self.extend_without_duplicates(results, [points[0], new_point, points[-1]])
            # if index != 0:
            #     new_p1 = self.find_new_p1(points[0], points[index], points[1:index], points1_are_not_removable, points[-1])
            # else:
            #     new_p1 = points[0]
            # if index != len(points):
            #     new_p3 = self.find_new_p1(points[-1], points[index], points[index+1:-1], points2_are_not_removable, points[0])
            # else:
            #     new_p3 = points[-1]
            # print(new_p3)
            # self.extend_without_duplicates(results, [new_p1, points[index], new_p3])
            # if not need_to_iterate:
            #     results = [points[0], points[index], points[-1]]
            # else:
            #     sub_polyline1_points = points[: index + 1]  # NOTE we include the max dist point
            #     sub_polyline2_points = points[index :]  # NOTE: we include the max dist point
            #     red_sub_polyline1 = self.douglas_peucker_algo(sub_polyline1_points, epsilon, True)
            #     red_sub_polyline2 = self.douglas_peucker_algo(sub_polyline2_points, epsilon, True)
            #     # results.extend(red_sub_polyline1)
            #     # results.extend(red_sub_polyline2)
            #     self.extend_without_duplicates(results, red_sub_polyline1)
            #     self.extend_without_duplicates(results, red_sub_polyline2)
            # print("NOW")
            # proj_1 = self.projected_point([15.651777267507015, 38.128523826513586], [[15.651286363574854, 38.12708604348619],[15.652104734945766, 38.12828767263811]])
            # print(proj_1)
            # print(mpltPath.Path(original_poly).contains_point(proj_1))
        return results

    def projected_point_old(self, point, line_points):
        if line_points[0][0] != line_points[1][0]:

            a = (line_points[0][1] - line_points[1][1]) / (line_points[0][0] - line_points[1][0])
            b = line_points[0][1] - a * line_points[0][0]

            # Then the coordinates of the projected point on y = ax + b is given by
            # x = (point[x] + a* point[y] - ab)/ (1 + a^2) and
            # y = (a* point[x] + a^2 * point[y] + b) / (1 + a^2)

            proj_x = (point[0] + a * point[1] - a*b) / (1 + a**2)
            proj_y = (a * point[0] + (a**2) * point[1] + b) / (1 + a**2)
        else:
            proj_x = line_points[0][0]
            proj_y = point[1]
        return [proj_x, proj_y]
    
    def projected_point(self, point, line_points):

        # x = np.array(point)

        # u = np.array(line_points[0])
        # v = np.array(line_points[len(line_points)-1])

        # n = v - u
        # n /= np.linalg.norm(n, 2)

        # P = u + n*np.dot(x - u, n)
        # return [P[0], P[1]]
        p1 = np.array(line_points[0])
        p2 = np.array(line_points[1])
        p3 = np.array(point)
        l2 = np.sum((p1-p2)**2)

        # The line extending the segment is parameterized as p1 + t (p2 - p1).
        # The projection falls where t = [(p3-p1) . (p2-p1)] / |p2-p1|^2

        # if you need the point to project on line extention connecting p1 and p2
        t = np.sum((p3 - p1) * (p2 - p1)) / l2

        projection = p1 + t * (p2 - p1)

        line_seg = [line_points[1][0]-line_points[0][0], line_points[1][1] - line_points[0][1]]
        proj_vect = [projection[0]-point[0], projection[1] - point[1]]
        # print("NOW")
        # print(line_seg[0] * proj_vect[0] + line_seg[1] * proj_vect[1])
        return [projection[0], projection[1]]
        # return [point[0] + 0.1 * proj_vect[0], point[1] + 0.1 * proj_vect[1]]

    def extend_without_duplicates(self, points, points_collection):
        for point in points_collection:
            assert len(point) == 2
            if point not in points:
                points.append(point)

    def iterate_under_tol(self):
        pass

    def find_max_angle_points(self, p1, p2, points, mask):
        # find the max angle between p1, p2 and a point in points
        # Note that we have a mask for the points however with some which shouldn't be taken into account

        new_points = [points[i]*mask[i] for i in range(len(mask))]

        max_angle = 0
        index = 0

        for i, point in enumerate(new_points):
            if len(point) != 0:
                angle = self.calc_angle(p1, p2, point)
                if angle > max_angle:
                    max_angle = angle
                    index = i

        return (max_angle, points[index])

    def find_intersection(self, line_seg1, line_seg2):
        # Find the intersection point between two line segments

        # find equation Ax + By + C = 0 of each line
        A1 = (line_seg1[0][1] - line_seg1[1][1])
        B1 = (line_seg1[1][0] - line_seg1[0][0])
        C1 = -(line_seg1[0][0] * line_seg1[1][1] - line_seg1[1][0]*line_seg1[0][1])

        A2 = (line_seg2[0][1] - line_seg2[1][1])
        B2 = (line_seg2[1][0] - line_seg2[0][0])
        C2 = -(line_seg2[0][0] * line_seg2[1][1] - line_seg2[1][0]*line_seg2[0][1])

        D = A1 * B2 - B1 * A2
        Dx = C1 * B2 - B1 * C2
        Dy = A1 * C2 - C1 * A2
        if D != 0:
            return [Dx/D, Dy/D]
        else:
            return line_seg1[1]

    def find_new_p1(self, p1, p2, points, mask, p3):
        # find the replacement point of p1, p1', between points such that this replacement point has all points under line p1'p2
        if len(points) == 0:
            return p1
        (max_angle_p1, max_point_p1) = self.find_max_angle_points(p1, p2, points, mask)
        if max_angle_p1 < 1e-8:
            return p1
        (max_angle_p3, max_point_p3) = self.find_max_angle_points(p2, p1, points, mask)
        if max_angle_p1 < 1e-8:
            return p1
        # line_seg1 = [p1, p3]
        line_seg1 = [p1, max_point_p3]
        line_seg2 = [p2, max_point_p1]
        p1p = self.find_intersection(line_seg1, line_seg2)
        return p1p

    def calc_angle(self, p1, p2, p3):
        # Calculates the angle at p2 using the law of cosines

        p1p2 = math.sqrt((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)
        p2p3 = math.sqrt((p2[0]-p3[0])**2 + (p2[1]-p3[1])**2)
        p1p3 = math.sqrt((p3[0]-p1[0])**2 + (p3[1]-p1[1])**2)

        enum = p1p2**2 + p2p3**2 - p1p3**2
        denom = 2 * p1p2 * p2p3
        if abs(enum/denom - 1) < 1e-8:
            return 0
        theta = math.acos(enum/denom)
        return theta

    def perp_dist(self, point, line_points):
        # project point onto the line

        # find line equation: y = ax + b
        # where a is the slope = (point1[y] - point2[y])/ (point1[x] - point2[x])
        # and b is the offset of the line = point1[y] - a* point1[x]

        if line_points[0][0] != line_points[1][0]:

            a = (line_points[0][1] - line_points[1][1]) / (line_points[0][0] - line_points[1][0])
            b = line_points[0][1] - a * line_points[0][0]

            # Then the coordinates of the projected point on y = ax + b is given by
            # x = (point[x] + a* point[y] - ab)/ (1 + a^2) and
            # y = (a* point[x] + a^2 * point[y] + b) / (1 + a^2)

            proj_x = (point[0] + a * point[1] - a*b) / (1 + a**2)
            proj_y = (a * point[0] + (a**2) * point[1] + b) / (1 + a**2)
        else:
            proj_x = line_points[0][0]
            proj_y = point[1]

        dist = math.sqrt((point[0] - proj_x)**2 + (point[1] - proj_y)**2)
        return dist
