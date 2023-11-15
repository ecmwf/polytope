def lerp(a, b, value):
    intersect = [b + (a-b) * value for a, b in zip(a, b)]
    return intersect
