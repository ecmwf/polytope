#
# # (C) Copyright 2021 ECMWF.
# #
# # This software is licensed under the terms of the Apache Licence Version 2.0
# # which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# # In applying this licence, ECMWF does not waive the privileges and immunities
# # granted to it by virtue of its status as an intergovernmental organisation
# # nor does it submit to any jurisdiction.
# ##
from . import array


def speed(*args, **kwargs):
    return array.speed(*args, **kwargs)


def direction(*args, **kwargs):
    return array.direction(*args, **kwargs)


def xy_to_polar(*args, **kwargs):
    return array.xy_to_polar(*args, **kwargs)


def polar_to_xy(*args, **kwargs):
    return array.polar_to_xy(*args, **kwargs)


def w_from_omega(*args, **kwargs):
    return array.w_from_omega(*args, **kwargs)


def coriolis(*args, **kwargs):
    return array.coriolis(*args, **kwargs)


def windrose(*args, **kwargs):
    return array.windrose(*args, **kwargs)
