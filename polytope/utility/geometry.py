import math


def lerp(a, b, value):
    direction = [a - b for a, b in zip(a, b)]
    intersect = [b + value * d for b, d in zip(b, direction)]
    return intersect


def nearest_pt(pts_list, pt):
    nearest_pt = pts_list[0]
    distance = l2_norm(pts_list[0], pt)
    for new_pt in pts_list[1:]:
        new_distance = l2_norm(new_pt, pt)
        if new_distance < distance:
            distance = new_distance
            nearest_pt = new_pt
    return nearest_pt


def l2_norm(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0]) * (pt1[0] - pt2[0]) + (pt1[1] - pt2[1]) * (pt1[1] - pt2[1]))
