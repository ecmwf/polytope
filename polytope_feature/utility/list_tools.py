import itertools


def bisect_left_cmp(arr, val, cmp):
    left = -1
    r = len(arr)
    while r - left > 1:
        e = (left + r) >> 1
        if cmp(arr[e], val):
            left = e
        else:
            r = e
    return left


def bisect_right_cmp(arr, val, cmp):
    left = -1
    r = len(arr)
    while r - left > 1:
        e = (left + r) >> 1
        if cmp(arr[e], val):
            left = e
        else:
            r = e
    return r


def unique(points):
    points.sort()
    points = [k for k, _ in itertools.groupby(points)]
    return points


def argmin(points):
    amin = min(range(len(points)), key=points.__getitem__)
    return amin


def argmax(points):
    amax = max(range(len(points)), key=points.__getitem__)
    return amax
