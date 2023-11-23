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
