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


class CollectionVisitor:
    def __init__(self, config, auth, logger):
        self.config = config
        self.auth = auth
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)

    # GET /api/v1/collections
    def list(self):
        """List available collections.

        Lists all available collections where to retrieve data from.

        :returns: list of collection IDs
        """
        situation = "trying to list collections"

        self._logger.info("Fetching collections...")
        url = self.config.get_url("collections")
        headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}
        method = "get"
        expected_responses = [requests.codes.ok]
        response, _ = helpers.try_request(
            method,
            situation=situation,
            expected=expected_responses,
            logger=self._logger,
            url=url,
            headers=headers,
            skip_tls=self.config.get()["skip_tls"],
        )
        found_collections = response.json()["message"]
        message = "The following collections are available:"
        ids_list = []
        for found_collection in found_collections:
            message += "\n  - " + found_collection
            ids_list.append(found_collection)
        self._logger.info(message)
        return ids_list

    def describe(self, collection_id):
        """Not yet implemented.

        To be defined.

        :arg collection_id: ID of the collection to describe.
        :type collection_id: str
        :returns: none
        """
        pass
