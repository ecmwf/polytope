import math


def lerp(a, b, value):
    intersect = [b + (a - b) * value for a, b in zip(a, b)]
    return intersect


def nearest_pt(pts_list, pt):
    new_pts_list = []
    for potential_pt in pts_list:
        for first_val in potential_pt[0]:
            for second_val in potential_pt[1]:
                new_pts_list.append((first_val, second_val))
    nearest_pt = new_pts_list[0]
    distance = l2_norm(new_pts_list[0], pt)
    for new_pt in new_pts_list[1:]:
        new_distance = l2_norm(new_pt, pt)
        if new_distance < distance:
            distance = new_distance
            nearest_pt = new_pt
    return nearest_pt


def l2_norm(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0]) * (pt1[0] - pt2[0]) + (pt1[1] - pt2[1]) * (pt1[1] - pt2[1]))
