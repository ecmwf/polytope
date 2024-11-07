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

import logging

import requests

from . import helpers


class Admin:
    def __init__(self, config, auth, logger=None):
        self.config = config
        self.auth = auth
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)

    # GET /api/v1/user
    def describe_user(self):
        """
        Show user information.

        Shows useful user information, such as the configured soft limit
        for that user and the number of currently live (non-revoked)
        requests on the server for the current user.

        :returns: None
        """
        situation = "trying to describe a user"

        url = self.config.get_url("users")
        headers = {"Content-Type": "application/json", "Authorization": ", ".join(self.auth.get_auth_headers())}
        method = "get"
        expected_responses = [requests.codes.ok]
        response, response_messages = helpers.try_request(
            method=method,
            situation=situation,
            expected=expected_responses,
            logger=self._logger,
            url=url,
            headers=headers,
            skip_tls=self.config.get()["skip_tls"],
        )

        message = "Information about the authenticated user received successfully:\n"
        for entry in response_messages:
            message += " - " + entry + ": " + response_messages[entry] + "\n"
        self._logger.info(message)

    # GET /api/v1/test
    def ping(self):
        """
        Check server availability.

        Informs whether the Polytope server (as specified in the Polytope
        client configuration address and port) is reachable and operating.

        See 'polytope list config' and 'polytope set config'.

        :returns: None
        """
        situation = "trying to ping the Polytope server for status"

        url = self.config.get_url("ping")
        method = "get"
        expected_responses = [requests.codes.ok]
        response, _ = helpers.try_request(
            method=method,
            situation=situation,
            expected=expected_responses,
            logger=self._logger,
            url=url,
            skip_tls=self.config.get()["skip_tls"],
        )
        message = "The Polytope server is operating and accessible."
        self._logger.info(message)
