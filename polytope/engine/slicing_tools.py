import scipy

from ..shapes import ConvexPolytope
from .hullslicer import _find_intersects

from matplotlib.colors import to_rgba
from matplotlib.patches import Polygon, Rectangle
from shapely.geometry import Polygon as Poly
from shapely.geometry import Point as Pt


def slice_in_two(polytope: ConvexPolytope, value, slice_axis_idx):
    if polytope is None:
        return (None, None)
    else:
        assert len(polytope.points[0]) == 2

        x_lower, x_upper, _ = polytope.extents(polytope._axes[slice_axis_idx])

        intersects = _find_intersects(polytope, slice_axis_idx, value)

        if len(intersects) == 0:
            if x_upper <= value:
                # The vertical slicing line does not intersect the polygon, which is on the left of the line
                # So we keep the same polygon for now since it is unsliced
                left_polygon = polytope
                right_polygon = None
            if value < x_lower:
                left_polygon = None
                right_polygon = polytope
        else:
            left_points = [p for p in polytope.points if p[slice_axis_idx] <= value]
            right_points = [p for p in polytope.points if p[slice_axis_idx] >= value]
            left_points.extend(intersects)
            right_points.extend(intersects)
            # find left polygon
            try:
                hull = scipy.spatial.ConvexHull(left_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                if "less than" or "is flat" in str(e):
                    # NOTE: this happens when we slice a polygon that has a border which coincides with the quadrant
                    # line and we slice this additional border with the quadrant line again.
                    # This is not actually a polygon we want to consider so we ignore it
                    vertices = None

            if vertices is not None:
                left_polygon = ConvexPolytope(polytope._axes, [left_points[i] for i in vertices])
            else:
                left_polygon = None

            try:
                hull = scipy.spatial.ConvexHull(right_points)
                vertices = hull.vertices
            except scipy.spatial.qhull.QhullError as e:
                # NOTE: this happens when we slice a polygon that has a border which coincides with the quadrant
                # line and we slice this additional border with the quadrant line again.
                # This is not actually a polygon we want to consider so we ignore it
                if "less than" or "is flat" in str(e):
                    vertices = None

            if vertices is not None:
                right_polygon = ConvexPolytope(polytope._axes, [right_points[i] for i in vertices])
            else:
                right_polygon = None

        return (left_polygon, right_polygon)


def visualise_slicing(polygon, slice_val, slice_axis_idx, camera, ax):
    import matplotlib.pyplot as plt
    from celluloid import Camera
    from IPython.display import Video

    fig, ax = plt.subplots(figsize=(4, 4))

    camera = Camera(fig)

    # NOTE: first picture
    # draw backdrop quadrant in all plots
    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.2)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)

    # draw initial polygon
    p_points = polygon.points
    poly = Polygon(p_points, facecolor='b')
    ax.add_patch(poly)
    camera.snap()

    # NOTE: second picture
    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.2)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)
    p_points = polygon.points
    poly = Polygon(p_points, facecolor='b')
    ax.add_patch(poly)
    # draw slicing line
    if slice_axis_idx == 0:
        # this means we slice vertically
        ax.axvline(slice_val, color='r')
        camera.snap()
    if slice_axis_idx == 1:
        # this means we slice horizontally
        ax.axhline(slice_val, color='r')
        camera.snap()

    # NOTE: third picture
    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.2)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)
    p_points = polygon.points
    poly = Polygon(p_points, facecolor='b')
    ax.add_patch(poly)
    # draw slicing line
    if slice_axis_idx == 0:
        # this means we slice vertically
        ax.axvline(slice_val, color='r')
    if slice_axis_idx == 1:
        # this means we slice horizontally
        ax.axhline(slice_val, color='r')
    (left_polygon, right_polygon) = slice_in_two(polygon, slice_val, slice_axis_idx)
    if left_polygon is not None:
        left_poly = Polygon(left_polygon.points, facecolor="c")
        ax.add_patch(left_poly)
    if right_polygon is not None:
        right_poly = Polygon(right_polygon.points, facecolor="m")
        ax.add_patch(right_poly)
    camera.snap()
    animation = camera.animate()
    plt.close()
    animation.save('slice_animation.gif', fps=1)  # Save the animation-- notes below
    Video("slice_animation.gif")  # Show the video you've just saved


def start_visualisation(polygon, points):
    import matplotlib.pyplot as plt
    from celluloid import Camera

    fig, ax = plt.subplots(figsize=(4, 4))

    camera = Camera(fig)
    (camera, ax, wanted_point) = base_frame(polygon, points, camera, ax)
    return (camera, ax, wanted_point)


def finish_visualisation(camera, ax):
    import matplotlib.pyplot as plt
    from IPython.display import Video
    animation = camera.animate()
    plt.close()
    animation.save('slice_animation_whole_v2.gif', fps=1)  # Save the animation-- notes below
    Video("slice_animation_whole_v2.gif")


def base_frame(polygon, points, camera, ax):
    from matplotlib.patches import Polygon
    # base region
    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.1)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)

    # base polygon and point cloud
    if polygon is not None:
        p_points = polygon.points
        poly = Polygon(p_points, facecolor='b')
        ax.add_patch(poly)
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")
        camera.snap()

        # find the point in point cloud that is within the polygon here
        poly_contains_point = False
        idx = 0
        wanted_point = []
        while not poly_contains_point:
            print("here")
            print(points)
            point = Pt(points[idx])
            print(point)
            # poly_contains_point = poly.contains_point(point)
            polygon_ = Poly(p_points)
            poly_contains_point = polygon_.contains(point)
            print(poly_contains_point)
            if poly_contains_point:
                wanted_point = point
            idx += 1
    return (camera, ax, wanted_point)


def find_point_in_point_cloud_within_polygon(points, polygon):

    if polygon is not None:
        p_points = polygon.points
        poly = Polygon(p_points, facecolor='b')

        # find the point in point cloud that is within the polygon here
        poly_contains_point = False
        idx = 0
        wanted_point = []
        while not poly_contains_point:
            point = points[idx]
            poly_contains_point = poly.contains_point(point)
            if poly_contains_point:
                wanted_point = point
            idx += 1
        return wanted_point


def first_frame(polygon, points, slice_val_vert, slice_val_hor, camera, ax):
    # draw the two horizontal and vertical slicing lines on top of the polygon

    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.1)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)

    # base polygon and point cloud
    if polygon is not None:
        p_points = polygon.points
        poly = Polygon(p_points, facecolor='b')
        ax.add_patch(poly)
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")

        # draw the horizontal and vertical slicing lines
        ax.axvline(slice_val_vert, color='r')
        ax.axhline(slice_val_hor, color="r")
        camera.snap()

    return (camera, ax)


def second_frame(q1_polygon, q2_polygon, q3_polygon, q4_polygon, wanted_point, points, camera, ax):
    polygon = find_right_sub_polygon(q1_polygon, q2_polygon, q3_polygon, q4_polygon, wanted_point)

    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.1)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)

    # base polygon and point cloud
    if polygon is not None:
        # p_points = polygon.points
        # poly = Polygon(p_points, facecolor='b')
        ax.add_patch(polygon)
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")
        camera.snap()

    return (camera, ax)


def add_visualisation_one_slice(polygon, q1_polygon, q2_polygon, q3_polygon, q4_polygon, wanted_point, points, slice_val_vert, slice_val_hor, camera, ax):
    (camera, ax) = first_frame(polygon, points, slice_val_vert, slice_val_hor, camera, ax)
    (camera, ax) = second_frame(q1_polygon, q2_polygon, q3_polygon, q4_polygon, wanted_point, points, camera, ax)
    return camera, ax


def find_right_sub_polygon(q1_polygon, q2_polygon, q3_polygon, q4_polygon, wanted_point):
    wanted_pt_ = Pt(wanted_point)
    right_poly = None
    if q1_polygon is not None:
        q1_p_points = q1_polygon.points

        q1_polygon_ = Poly(q1_p_points)

        q1_poly = Polygon(q1_p_points, facecolor="b")
        if q1_polygon_.contains(wanted_pt_):
            right_poly = q1_poly
    if q2_polygon is not None:
        q2_p_points = q2_polygon.points
        q2_polygon_ = Poly(q2_p_points)
        q2_poly = Polygon(q2_p_points, facecolor="b")
        if q2_polygon_.contains(wanted_pt_):
            right_poly = q2_poly
    if q3_polygon is not None:
        q3_p_points = q3_polygon.points
        q3_polygon_ = Poly(q3_p_points)
        q3_poly = Polygon(q3_p_points, facecolor="b")
        if q3_polygon_.contains(wanted_pt_):
            right_poly = q3_poly
    if q4_polygon is not None:
        q4_p_points = q4_polygon.points
        q4_polygon_ = Poly(q4_p_points)
        q4_poly = Polygon(q4_p_points, facecolor="b")
        if q4_polygon_.contains(wanted_pt_):
            right_poly = q4_poly
    return right_poly


def add_visualisation_bits(polygon, slice_val, slice_axis_idx, camera, ax, points):
    # NOTE: first picture
    # draw backdrop quadrant in all plots
    (camera, ax) = plot_first_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points)

    # NOTE: second picture
    (camera, ax) = plot_second_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points)

    # NOTE: third picture
    (camera, ax) = plot_third_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points)
    return (camera, ax)


def plot_first_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):

    # NOTE: first picture
    # draw backdrop quadrant in all plots
    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.1)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)

    # draw initial polygon
    if polygon is not None:
        p_points = polygon.points
        poly = Polygon(p_points, facecolor='b')
        ax.add_patch(poly)
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")
        camera.snap()
    return (camera, ax)


def plot_second_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):

    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.1)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)
    if polygon is not None:
        p_points = polygon.points
        poly = Polygon(p_points, facecolor='b')
        ax.add_patch(poly)
        # draw slicing line
        if slice_axis_idx == 0:
            # this means we slice vertically
            ax.axvline(slice_val, color='r')
            points_x = [p[0] for p in points]
            points_y = [p[1] for p in points]
            ax.scatter(points_x, points_y, color="grey")
            camera.snap()
        if slice_axis_idx == 1:
            # this means we slice horizontally
            ax.axhline(slice_val, color='r')
            points_x = [p[0] for p in points]
            points_y = [p[1] for p in points]
            ax.scatter(points_x, points_y, color="grey")
            camera.snap()
    return (camera, ax)


def plot_third_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):

    ax.add_patch(Rectangle((-180, -90), 360, 180, fc=to_rgba('blue', 0.1)))
    ax.set_xlim(-200, 200)
    ax.set_ylim(-100, 100)
    if polygon is not None:
        p_points = polygon.points
        poly = Polygon(p_points, facecolor='b')
        ax.add_patch(poly)
        # draw slicing line
        if slice_axis_idx == 0:
            # this means we slice vertically
            ax.axvline(slice_val, color='r')
        if slice_axis_idx == 1:
            # this means we slice horizontally
            ax.axhline(slice_val, color='r')
        (left_polygon, right_polygon) = slice_in_two(polygon, slice_val, slice_axis_idx)
        # if left_polygon is not None:
        #     left_poly = Polygon(left_polygon.points, facecolor="c")
        #     ax.add_patch(left_poly)
        if right_polygon is not None:
            right_poly = Polygon(right_polygon.points, facecolor="m")
            ax.add_patch(right_poly)
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")
        camera.snap()

        if right_polygon is not None and left_polygon is not None:
            camera, ax = plot_fourth_slice_frame(right_polygon, slice_val, slice_axis_idx, camera, ax, points)

    return (camera, ax)


def plot_fourth_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):

    p_points = polygon.points
    poly = Polygon(p_points, facecolor="b")
    ax.add_patch(poly)
    points_x = [p[0] for p in points]
    points_y = [p[1] for p in points]
    ax.scatter(points_x, points_y, color="grey")
    camera.snap()
    return (camera, ax)
