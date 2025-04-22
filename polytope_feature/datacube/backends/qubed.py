import logging
import operator
from copy import deepcopy
from itertools import product

from .datacube import Datacube, TensorIndexTree


class QubedDatacube(Datacube):

    def __init__(
        self, q, datacube_axes, datacube_transformations, config=None, axis_options=None, compressed_axes_options=[], alternative_axes=[], context=None
    ):
        self.q = q
        # TODO: find datacube_axes and datacube_transformations from options like other datacube backends
        self.datacube_axes = datacube_axes
        self.datacube_transformations = datacube_transformations
        # TODO: find compressed_axes list
        self.compressed_axes = []
        self._axes = datacube_axes

    def get(self, requests: TensorIndexTree, context):
        # TODO: use GJ to extract data from an fdb
        return requests
