import time
import logging


class benchmark(object):
    def __init__(self, name):
        self.name = name

    def __enter__(self):
        self.start = time.perf_counter()

    def __exit__(self, ty, val, tb):
        end = time.perf_counter()
        print("%s : %0.7f seconds" % (self.name, end - self.start))
        return False


def timing_fn(func):
    def wrapper(*arg, **kw):
        t1 = time.perf_counter()
        res = func(*arg, **kw)
        time_taken = time.perf_counter() - t1
        fn_name = func.__name__
        logging.debug("Time taken for %s is %s seconds", fn_name, time_taken)
        return res
    return wrapper
