import math

try:
    from polytope_feature.polytope_rs import nearest_pt as _rs_nearest_pt

    _RUST_NEAREST_PT = True
except ImportError:
    _RUST_NEAREST_PT = False


def lerp(a, b, value):
    intersect = [b + (a - b) * value for a, b in zip(a, b)]
    return intersect


def nearest_pt(pts_list, pt, k=1):
    """Return the k nearest points from pts_list to pt.

    pts_list is a list of items like [lat_values, lon_values]; we expand
    each into all combinations (lat, lon) and compute Euclidean distance
    to `pt`. If k==1 a single tuple is returned, otherwise a list of tuples
    ordered by increasing distance is returned.
    """
    if _RUST_NEAREST_PT:
        # Convert to the format expected by Rust: list of (lat_vals, lon_vals) tuples
        rs_input = [(list(item[0]), list(item[1])) for item in pts_list]
        result = _rs_nearest_pt(rs_input, (float(pt[0]), float(pt[1])), int(k))
        if not result:
            return [] if k != 1 else None
        return result

    # Pure-Python fallback
    new_pts_list = []
    for potential_pt in pts_list:
        for first_val in potential_pt[0]:
            for second_val in potential_pt[1]:
                new_pts_list.append((first_val, second_val))

    if not new_pts_list:
        return [] if k != 1 else None

    # compute distances
    dist_pts = [(l2_norm(p, pt), p) for p in new_pts_list]
    dist_pts.sort(key=lambda x: x[0])
    best = [p for _, p in dist_pts[:k]]
    return best


def l2_norm(pt1, pt2):
    return math.sqrt((pt1[0] - pt2[0]) * (pt1[0] - pt2[0]) + (pt1[1] - pt2[1]) * (pt1[1] - pt2[1]))
