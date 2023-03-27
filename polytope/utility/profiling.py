import time


class benchmark(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()

    def __exit__(self, ty, val, tb):
        end = time.perf_counter()
        print("%s : %0.7f seconds" % (self.name, end - self.start))
        return False
