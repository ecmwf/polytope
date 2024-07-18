# (C) Copyright 2021 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


"""
Solar computation functions.

The API is split into two levels. The low level functions are in the ``array`` submodule and they
can be used to operate on numpy arrays. The high level functions are still to be developed and
planned to work with objects like *earthkit.data FieldLists* or *xarray DataSets*
"""

from .solar import *  # noqa
