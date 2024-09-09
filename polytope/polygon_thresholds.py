def restrict_points(points, Nmax):
    if len(points) > Nmax:
        raise ValueError("Too many points in Polygon")
    return points


def area_polygon(points):
    # Use Green's theorem, see
    # https://stackoverflow.com/questions/256222/which-exception-should-i-raise-on-bad-illegal-argument-combinations-in-python
    return 0.5 * abs(sum(x0*y1 - x1*y0
                         for ((x0, y0), (x1, y1)) in segments(points)))


def segments(points):
    return zip(points, points[1:] + [points[0]])


def restrict_area(points, Nmax, Amax):
    points = restrict_points(points, Nmax)
    area = area_polygon(points)
    if area > Amax:
        raise ValueError("Polygon is too large")
    return points


if __name__ == "__main__":
    polygon_points = [[1, 1], [2, 1], [2, 2], [1, 2]]
    assert area_polygon(polygon_points) == 1
    polygon_points = [[1, 1], [1, 2], [2, 2], [2, 1]]
    assert area_polygon(polygon_points) == 1
    polygon_points = [[1, 1], [1, 3], [2, 3], [2, 1]]
    assert area_polygon(polygon_points) == 2

    try:
        restrict_area(polygon_points, 5, 1)
    except ValueError as e:
        assert str(e) == "Polygon is too large"
    try:
        restrict_area(polygon_points, 2, 3)
    except ValueError as e:
        assert str(e) == "Too many points in Polygon"
