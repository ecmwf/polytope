# Copyright 2021 European Centre for Medium-Range Weather Forecasts (ECMWF)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.

"""This sub-module, the Polytope client API, contains a number of python
classes with methods to perform all possible operations against a Polytope
server. These methods can be used directly from within a python session
through the Client class, which exposes all user-relevant methods. Also,
these methods are called automatically by the commands in the CLI provided
also as part of the Polytope client."""

# Creating a top-level logger named 'polytope'.
# Lower-level loggers are added to it as children and used within the API to
# register log messages.
# The logger has no handler actions (i.e. logs are ignored by default).
# The polytope CLI internally adds a handler to this logger as well.
import logging

from .Client import Client

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
logger.addHandler(logging.NullHandler())

# An API user can add handlers (in order to print logs onto stderr or log
# file) as follows:
#
#  import polytope.api
#  import logging
#  logger = logging.getLoger('polytope')
#
#  # create console handler and set level to debug
#  ch = logging.StreamHandler()
#  ch.setLevel(logging.WARNING)
#
#  # create formatter
#  fm = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#  # add formatter to ch
#  ch.setFormatter(fm)
#
#  # add ch to logger
#  logger.addHandler(ch)

__all__ = ["Client"]
