import scipy

from ..shapes import ConvexPolytope
from .hullslicer import _find_intersects


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
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Polygon, Rectangle

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


def start_visualisation():
    import matplotlib.pyplot as plt
    from celluloid import Camera

    fig, ax = plt.subplots(figsize=(4, 4))

    camera = Camera(fig)
    return (camera, ax)


def finish_visualisation(camera, ax):
    import matplotlib.pyplot as plt
    from IPython.display import Video
    animation = camera.animate()
    plt.close()
    animation.save('slice_animation_whole.gif', fps=1)  # Save the animation-- notes below
    Video("slice_animation_whole.gif")


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
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Polygon, Rectangle

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
        # TODO: add the points on the quadtree
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")
        camera.snap()
    return (camera, ax)


def plot_second_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Polygon, Rectangle

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
            # TODO: add points on the quadtree
            points_x = [p[0] for p in points]
            points_y = [p[1] for p in points]
            ax.scatter(points_x, points_y, color="grey")
            camera.snap()
        if slice_axis_idx == 1:
            # this means we slice horizontally
            ax.axhline(slice_val, color='r')
            # TODO: add points on the quadtree
            points_x = [p[0] for p in points]
            points_y = [p[1] for p in points]
            ax.scatter(points_x, points_y, color="grey")
            camera.snap()
    return (camera, ax)


def plot_third_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):
    from matplotlib.colors import to_rgba
    from matplotlib.patches import Polygon, Rectangle
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
        # TODO: add points on the quadtree
        points_x = [p[0] for p in points]
        points_y = [p[1] for p in points]
        ax.scatter(points_x, points_y, color="grey")
        camera.snap()

    return (camera, ax)


def plot_fourth_slice_frame(polygon, slice_val, slice_axis_idx, camera, ax, points):
    pass
