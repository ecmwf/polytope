
def lerp(a, b, value):
    direction = [a-b for a,b in zip(a,b)]
    intersect = [b+ value*d for b,d in zip(b, direction)]
    return intersect