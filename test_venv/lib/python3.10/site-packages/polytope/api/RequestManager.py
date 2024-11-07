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

import collections
import copy
import hashlib
import logging
import os
import pprint
import random
import string
import time
from pathlib import Path

import requests
import yaml
from tqdm import tqdm

from . import helpers
from .Result import Result


class RequestManager:
    def __init__(self, config, auth, coll_visitor, logger=None):
        self.config = config
        self.auth = auth
        self.coll_visitor = coll_visitor
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)

    # GET /api/v1/requests
    # GET /api/v1/requests/<collection_id>
    def list(self, collection_id=None):
        """
        List active requests.

        Lists all active (non-revoked) requests for the current user.
        The ID and status of each request is shown.

        :param collection_id: Name of a collection to filter found requests
        (optional).
        :type collection_id: str
        :returns: list of active request IDs.
        """
        situation = "trying to list requests"

        self._logger.info("Fetching requests...")
        url = self.config.get_url("requests", collection_id=collection_id)
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
        found_requests = response.json()["message"]
        message = "The authenticated user has " + str(len(found_requests)) + " active requests"
        ids_list = []
        for found_request in found_requests:
            message += "\n  - " + found_request["id"]
            message += " (" + found_request["status"] + ")"
            message += " (" + found_request["verb"] + ")"
            ids_list.append(found_request["id"])
        self._logger.info(message)
        return ids_list

    # GET /api/v1/requests/ + client-side filtering
    def describe(self, request_id):
        """
        Describe a request.

        Shows the JSON schema of a given request. The IDs of the requests
        can be listed with 'polytope list requests'.

        :param request_id: ID or URL of the target request.
        :type request_id: str
        :returns: Dictionary with description items.
        """
        situation = "trying to describe a request"

        if "://" in request_id:
            request_id = request_id.split("/")[-1]

        self._logger.info("Fetching request...")
        url = self.config.get_url("requests")
        headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}
        method = "get"
        expected_responses = [requests.codes.ok]
        response, response_messages = helpers.try_request(
            method,
            situation=situation,
            expected=expected_responses,
            logger=self._logger,
            url=url,
            headers=headers,
            skip_tls=self.config.get()["skip_tls"],
        )
        found_requests = response.json()["message"]
        description = None
        for found_request in found_requests:
            if found_request["id"] == request_id:
                description = found_request
                break
        if not description:
            e = helpers.PolytopeError(situation)
            e.description = "Describe failed: request %s not found" % request_id
            raise e
        message = "Received request description:\n" + pprint.pformat(description)
        self._logger.info(message)

        return description

    # DELETE /api/v1/requests/<request_id>
    def revoke(self, request_id):
        """
        Revoke a request.

        Revokes a previously issued request. Upon completion, any data
        associated to the request is removed from the Polytope server.

        :param request_id: ID or URL of the target request, or 'all' to remove all
        existing user requests.
        :type request_id: str
        :returns: None
        """
        situation = "trying to revoke a request"

        headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}

        if request_id == "all":
            request_ids = self.list()
        else:
            request_ids = [request_id]

        for id in request_ids:
            self._logger.info("Revoking request " + id + "...")
            method = "delete"
            if "://" in id:
                url = id
            else:
                url = self.config.get_url("requests", id)
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
            self._logger.info("Request deleted successfully")

    # POST /api/v1/requests/<collection> with verb = retrieve
    # and, implicitly after automatic 303 redirect:
    # GET /api/v1/downloads/<request_id>
    def retrieve(
        self,
        name,
        request,
        output_file=None,
        inline_request=True,
        asynchronous=False,
        max_attempts=None,
        attempt_period=0.1,
        append=False,
        pointer=False,
    ):
        """
        Request retrieval of data.

        Submits a request for data retrieval to the Polytope server.

        A request must be specified either inline or from a YAML file, as
        described in detail below, always following the MARS request syntax,
        as shown in

            https://confluence.ecmwf.int/display/UDOC/MARS+command+and+request+syntax

        An inline request can be specified in two ways: as character string
        containing or as a Python dictionary (the latter is only available
        if using the Python API).

            - character string: "key = valye, key = value, ..."

            - python dictionary: {'key': 'value', 'key': 'value', ...}

        If specified as a YAML file, it must be in the format

            key: value
            key: value
            ...

        or

            {
                'key': 'value',
                'key': 'value',
                ...
            }

        If willing to collect data from multiple requests into a single
        file, a list with multiple requests to be retrieved can also be
        provided if using the API (as a list of dictionaries) or if using
        a YAML file (a single YAML file can be specified at once, containing
        a YAML list of requests). E.g.:

        if using the Python API:

            [{'key': 'value', 'key': 'value', ...}, {'key': 'value', 'key': 'value', ...}, ...]

        or, if using a YAML file:

            - key: value
              key: value
              ...
            - key: value
              key: value
              ...
            ...

        or, in a YAML file with the JSON sub-syntax:

            [{
                'key': 'value',
                'key': 'value',
                ...
             },
             {
                'key': 'value',
                'key': 'value',
                ...
             },
             ...]

        In all cases, the request specifications must follow the MARS request
        syntax for the keywords and values, as referenced above.

        The name of the Polytope collection where to retrieve the data
        from must be specified via the first mandatory parameter 'name'.
        See 'polytope list requests' (if using the Polytope CLI) or
        'Client.list_requests' (if using the python API). The only
        collection available as of this client version is 'ecmwf-mars'.

        If the request is specified inline, the flag inline_request must be
        set to True.

        When submitting a retrieval request, the Polytope server may return
        data immediately if already available on the server, or may simply
        file the request and process it when possible. In that later case,
        if the flag 'asynchronous' is set to False, the client will wait for
        the server to process the request and return the data.

        An output file where to store the data must be specified, in case
        the 'asynchronous' flag is set (read below) or in case the server
        returns data immediately.

        :param name: Name of the Polytope collection where to retrieve the
        data from. E.g. 'ecmwf-mars'.
        :type name: str
        :param request: An inline request (specified as a YAML string or as
        a python dictionary if using the API) or a path to a YAML request
        file (containing one or a list of JSON requests).
        :type request: str
        :param output_file: Path to a file where to store the data.
        It will overwritten if existing, or created if not existing.
        If an output_file is not specified, a random output file name will
        be chosen. This parameter is ignored if the parameter 'pointer' is
        set to True (as no data is downloaded).
        :type output_file: str
        :param inline_request: Flag to indicate whether the provided
        request is an inline request or a path to a YAML request file.
        :type inline_request: bool
        :param asynchronous: Whether to wait for the server to process
        the request (False) in case the data is not already present in
        the Polytope server, or not (True).
        :type asynchronous: bool
        :param max_attempts: Maximum number of retrials in case the data
        is not immediately available on the server. It takes the value None
        by default, which means the command will retry until the data
        becomes available or until the server notifies the request has failed.
        :type max_attempts: int
        :param attempt_period: Initial amount of time to wait, in seconds,
        between download retrials in case the data is not found directly on
        the server. This amount, which takes the value 0.1 by default, is
        increased at a rate of 1.2x each iteration (maxing out at 120 seconds).
        :type attempt_period: int
        :param append: Whether to append the downloaded data to the specified
        'output_file', or to overwrite the destination file. False by default.
        :type append: bool
        :param pointer: Whether to return the data as a logical representation
        in the format {'location': <URL>, 'contentLength': <number_of_bytes>}
        (pointer = True) or to download the data onto a file (pointer = False;
        default).
        :type pointer: bool
        :returns: None
        """
        situation = "trying to submit a retrieval request"

        # replaced_level = helpers.lower_stream_handler_level(self._logger)
        # helpers.lower_stream_handler_level(self._logger)
        # colls = self.coll_visitor.list()
        # helpers.recover_stream_handler_level(self._logger, replaced_level)
        # if name not in colls:
        #     raise ValueError("Collection name '" + name + "' not available.")

        if not inline_request:
            self._logger.info("Reading request file...")
            request = os.path.expanduser(request)
            # If we receive a file, pass it on as a string
            with open(request, "r") as request_file_handler:
                request = request_file_handler.read()
        else:
            # If we receive a Python dictionary, encode it as yaml
            # TODO: we don't know what the eventual data source requires,
            # encoding to YAML is the most flexible approach for now, but
            # this needs a more robust solution.
            if isinstance(request, dict):
                request = yaml.safe_dump(request)
            # else try to convert plainly to string
            else:
                request = str(request)
        if not isinstance(request, list):
            user_requests = [request]
        else:
            user_requests = request

        request_ids_pending_for_download = []
        request_urls_pending_for_download = []
        request_results = []
        warnings = []
        for request in user_requests:
            collection = name
            request_object = {"verb": "retrieve", "request": request}

            message = "Sending request...\n" + pprint.pformat(request_object)
            self._logger.info(message)

            url = self.config.get_url("requests", collection_id=collection)
            headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}
            method = "post"
            expected_responses = [requests.codes.ok, requests.codes.accepted, requests.codes.no_content]
            # also requests.codes.other, implicitly handled by requests
            # when POSTing to a URL with redirection, requests will do a GET
            # against the new URL
            response, response_messages = helpers.try_request(
                method,
                situation=situation,
                expected=expected_responses,
                logger=self._logger,
                url=url,
                headers=headers,
                json=request_object,
                stream=True,
                skip_tls=self.config.get()["skip_tls"],
            )
            # According to 'REST API, Copernicus CDS, 02/06/2019':
            # 303 see other: redirection to direct download endpoint
            # 202 accepted: redirection to polling endpoint
            # 200 ok: direct Json or binary data
            if response.status_code == requests.codes.ok:
                if any(request_ids_pending_for_download):
                    warning = (
                        "Some of the requested data were "
                        + "received immediately and some others were not. "
                        + "The resulting data file will not be in the same "
                        + "order as the requests submitted for retrieval."
                    )
                    if warning not in warnings:
                        warnings.append(warning)
                if pointer:
                    e = helpers.PolytopeError(situation=situation)
                    e.description = "Receipt of pointer on POST " + "to /requests/<collection_id> not yet implemented"
                    raise e
                    location = response.headers.get("Location")
                    content_length = response.headers.get("Content-Length")
                    result = {"location": location, "contentLength": content_length}
                    if self.config._cli:
                        print(pprint.pformat(result))
                    request_results.append(result)
                else:
                    self._logger.info("The data is immediately available for download")
                    result_file = self._download(response, output_file, append)
                    if not output_file:
                        output_file = result_file
                    append = True
                    request_results.append(result_file)
                request_ids_pending_for_download.append(None)
                request_urls_pending_for_download.append(None)
            elif response.status_code == requests.codes.accepted:
                location = response.headers.get("Location")
                request_id = location.split("/")[-1]
                self._logger.info("Request accepted. Please poll %s for status" % location)
                self._logger.debug("Server message: %s" % response_messages["message"])
                request_ids_pending_for_download.append(request_id)
                request_urls_pending_for_download.append(location)
                request_results.append(None)
            elif response.status_code == requests.codes.no_content:
                self._logger.info(
                    "The data requested is not "
                    + "available yet on the Polytope server, but will be in the "
                    + "future. Please check the Polytope catalogue"
                )

        if len(user_requests) > 1 and not output_file:
            output_file = "+".join(request_ids_pending_for_download) + ".grib"

        for i, request_url in enumerate(request_urls_pending_for_download):
            if not request_url:
                continue

            if asynchronous:
                if not append and not self.config._cli and i > 0:
                    warning = (
                        "Multiple requests have been "
                        + "submitted asynchronously, and a Result object "
                        + "has been returned for each of them. The first "
                        + "Result should be downloaded first, which will "
                        + "create/overwrite the destination file. Otherwise, "
                        + "if any of the other Results is downloaded first, "
                        + "the file may be wiped when the first Result in "
                        + "the returned list is downloaded."
                    )
                    if warning not in warnings:
                        warnings.append(warning)
                request_results[i] = Result(request_url, output_file, append, self)
            else:
                request_results[i] = self.download(
                    request_url, output_file, asynchronous, max_attempts, attempt_period, append, pointer
                )

            append = True

        for warning in warnings:
            self._logger.warning(warning)

        return request_results

    def _download_to_file(self, response, output_file, append):
        situation = "trying to download data"
        output_file = os.path.expanduser(output_file)
        self._logger.info("Saving data into {}...".format(output_file))
        start = time.time()
        data_downloaded = False
        total_received = 0
        if append:
            mode = "ab"
        else:
            mode = "wb"
        attempts = 1
        http_max_attempts = 10
        new_attempt_period = 10
        # hash_md5 = hashlib.md5()
        content_length = int(response.headers["Content-Length"])
        # checksum = response.headers['Content-MD5']
        while not data_downloaded:
            try:
                with tqdm(
                    total=content_length,
                    unit_scale=True,
                    unit_divisor=1024,
                    unit="B",
                    disable=self.config.get()["quiet"],
                    leave=False,
                ) as pbar:
                    pbar.update(total_received)
                    with open(output_file, mode) as output_handler:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                output_handler.write(chunk)
                                # hash_md5.update(chunk)
                                total_received += len(chunk)
                                pbar.update(len(chunk))
            except requests.exceptions.ConnectionError as e:
                self._logger.warning("Download interrupted: " + str(e))
            finally:
                response.close()

            if total_received >= content_length:
                data_downloaded = True
                self._logger.info("Data downloaded successfully")
                break

            self._logger.warning(
                ("Download incomplete, downloaded %s " + "byte(s) out of %s") % (total_received, content_length)
            )

            method = response.request.method.lower()
            url = response.request.url
            headers = response.request.headers
            # json = response.request.json()

            attempts += 1
            if attempts > http_max_attempts:
                e = helpers.GivenUpDownloadError(
                    situation=situation,
                    url=url,
                    method=method,
                    request_content={"headers": headers},  # , 'json': json},
                    attempts=http_max_attempts,
                )
                raise e

            mode = "ab"
            self._logger.warning("Sleeping %s seconds" % new_attempt_period)
            time.sleep(new_attempt_period)
            total_received = os.path.getsize(output_file)
            headers["Range"] = "bytes=%d-" % (total_received)
            self._logger.warning("Resuming download at byte %s" % total_received)

            expected_responses = [requests.codes.ok]
            response.close()
            response, _ = helpers.try_request(
                method,
                situation=situation,
                expected=expected_responses,
                logger=self._logger,
                stream=True,
                url=url,
                headers=headers,
                skip_tls=self.config.get()["skip_tls"],  # , json = json
            )

        e = helpers.PolytopeError(situation)
        if total_received != content_length:
            e.description = ("Download failed: downloaded %s byte(s) out of " + "%s") % (total_received, content_length)
            raise e

        elapsed = time.time() - start
        if elapsed:
            self._logger.info(("Download rate %s/s") % helpers.bytes_to_string(content_length / elapsed))

        # if hash_md5.hexdigest() != checksum:
        #    e = helpers.PolytopeError(situation)
        #    e.description = ("Download failed: checksum of downloaded data " +
        #        "does not match the expected checksum.")
        #    raise e

        self._logger.info("Data saved successfully into " + output_file)
        return output_file

    def _download(self, response, output_file, append, request_id=None):
        situation = "trying to download data"

        content_type = response.headers.get("Content-Type", None)
        self._logger.info("Starting data download (" + content_type + ")...")
        if not content_type:
            e = helpers.BugError(situation=situation)
            e.description = "Content-Type header not found in the response"
            raise e
        if content_type == "application/prs.coverage+json":
            if not output_file:
                self._logger.info(
                    "Parameter 'output_file' not " + "provided, proceeding to save data into a " + "temporary file..."
                )
                if request_id:
                    output_file = request_id + ".covjson"
                else:
                    random_id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
                    output_file = "tmp" + random_id + ".covjson"
            return self._download_to_file(response, output_file, append)
        elif content_type == "application/octet-stream":
            if output_file:
                output_file = os.path.expanduser(output_file)
                if append:
                    mode = "ab"
                else:
                    mode = "wb"
                with open(output_file, mode) as output_file_handler:
                    output_file_handler.write(response.content)
                self._logger.info("Data (" + content_type + ") saved successfully into " + output_file)
                return output_file
            return response.content
        elif content_type == "application/x-grib":
            if not output_file:
                self._logger.info(
                    "Parameter 'output_file' not " + "provided, proceeding to save data into a " + "temporary file..."
                )
                if request_id:
                    output_file = request_id + ".grib"
                else:
                    random_id = "".join(random.choices(string.ascii_letters + string.digits, k=16))
                    output_file = "tmp" + random_id + ".grib"
            return self._download_to_file(response, output_file, append)
        else:
            e = helpers.BugError(situation=situation)
            e.description = "Received unsupported content type: " + content_type
            raise e

    # GET /api/v1/requests/<request_id>
    # and, implicitly after automatic 303 redirect:
    # GET /api/v1/downloads/<request_id>
    def download(
        self,
        request_id,
        output_file=None,
        asynchronous=False,
        max_attempts=None,
        attempt_period=0.1,
        append=False,
        pointer=False,
    ):
        """
        Download data of a request.

        Downloads the data of a previously issued retrieval request.

        :param request_id: ID or URL of the request which to download the data for.
        :type request_id: str
        :param output_file: Path to a file where to store the data.
        It will overwritten if existing, or created if not existing.
        If an output_file is not specified, a random output file name will
        be chosen. This parameter is ignored if the parameter 'pointer' is
        set to True (as no data is downloaded).
        :type output_file: str
        :param asynchronous: Whether to wait for the server to process
        the request (False) in case the data is not already present in
        the Polytope server, or not (True).
        :type asynchronous: bool
        :param max_attempts: Maximum number of retrials in case the data
        is not immediately available on the server. It takes the value None
        by default, which means the command will retry until the data
        becomes available or until the server notifies the request has failed.
        :type max_attempts: int
        :param attempt_period: Initial amount of time to wait, in seconds,
        between download retrials in case the data is not immediately
        available on the server. This amount, which takes the value 0.1 by
        default, is increased at a rate of 1.2x each iteration (maxing out at
        120 seconds).
        :type attempt_period: int
        :param append: Whether to append the downloaded data to the specified
        'output_file', or to overwrite the destination file. False by default.
        :type append: bool
        :param pointer: Whether to return the data as a logical representation
        in the format {'location': <URL>, 'contentLength': <number_of_bytes>}
        (pointer = True) or to download the data onto a file (pointer = False;
        default).
        :type pointer: bool
        :returns: None
        """
        if not max_attempts:
            max_attempts = float("inf")

        situation = "trying to download data"

        data_ready = False
        status = None
        attempts = 1
        describe_max_attempts = max_attempts
        if asynchronous:
            describe_max_attempts = 1
        new_attempt_period = attempt_period
        max_attempt_period = 120
        if "://" in request_id:
            url = request_id
            request_id = url.split("/")[-1]
        else:
            url = self.config.get_url("requests", request_id=request_id)
        headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}
        method = "get"
        expected_responses = [requests.codes.ok, requests.codes.accepted]
        # requests will handle automatically requests.codes.other
        self._logger.info("Checking request status (" + request_id + ")...")
        while not data_ready:
            if attempts > describe_max_attempts:
                e = helpers.RetriesExceededError(
                    attempts=describe_max_attempts, situation=situation, url=url, method=method, request_content=headers
                )
                raise e
            response, response_messages = helpers.try_request(
                method,
                situation=situation,
                expected=expected_responses,
                logger=self._logger,
                stream=True,
                url=url,
                headers=headers,
                skip_tls=self.config.get()["skip_tls"],
            )
            if response.status_code == requests.codes.ok:
                last_status = "processed"
                server_message = None
            else:
                last_status = response_messages["status"]
                server_message = response_messages["message"]
            if last_status == "failed":
                e = helpers.PolytopeError(situation)
                e.description = "The request failed with the following error:\n"
                e.description += response_messages["message"]
                raise e
            if status != last_status:
                status = last_status
                self._logger.info("The current status of the " + "request is '" + status + "'")
                if server_message:
                    self._logger.debug("Server message: %s" % server_message)
            data_ready = status == "processed"
            if not data_ready:
                # retry_after = response.headers.get("Retry-After", None)
                if not asynchronous:
                    time.sleep(new_attempt_period)
                attempts = attempts + 1
                new_attempt_period *= 1.2
                new_attempt_period = min(new_attempt_period, max_attempt_period)

        if pointer:
            result = {
                "location": response.url,
                "contentLength": response.headers.get("Content-Length"),
                "contentType": response.headers.get("Content-Type"),
            }
            if self.config._cli:
                print(pprint.pformat(result))
            return result

        return self._download(response, output_file, append, request_id)

    # POST /api/v1/requests/<collection> with verb = archive
    def archive(
        self, name, metadata, input_url, inline_metadata=True, asynchronous=False, max_attempts=None, attempt_period=0.1
    ):
        """
        Request archival of data.

        Submits a request for data archival to the Polytope server.

        The metadata of the uploaded data must be specified either inline
        (as a string in the "key = valye, key = value, ..." format or
        alternatively, if using the API, as a ptyhon dictionary in the
        {'key': 'value', 'key': 'value', ...} format) or from a YAML file.
        In all cases the metadata must follow the MARS request syntax.

        The name of the Polytope collection where to archive the data
        must be specified via the first mandatory parameter 'name'.
        See 'polytope list requests' (if using the Polytope CLI) or
        'Client.list_requests' (if using the python API). The only
        collection available as of this client version is 'ecmwf-mars'.

        If the metadata is specified inline, the flag inline_metadata must be
        set to True.

        When submitting an archival request, the data to upload must be
        specified either via a URL to an HTTP server where the Polytope server
        will retrieve the data from, or via a path to a local file. When using
        a URL, after subitting the archival request, the server will respond
        with a URL were to poll for the status of the data being uploaded.
        If the flag 'asynchronous' is set to False, the client will wait for
        the server to fetch the data from the HTTP server before it is
        made available for further retrieval.

        When using a path, the server will respond with an URL where to
        upload the data. If the flag 'asynchronous' is set to False, the
        client will wait for the server to fully process the data before it is
        made available for further retrieval.

        :param name: Name of the Polytope collection where to retrieve the
        data from. E.g. 'ecmwf-mars'.
        :type name: str
        :param metadata: An inline metadata specification (specified as a
        YAML string or as a python dictionary if using the API) or a path
        to a YAML metadata file.
        :type metadata: str
        :param input_url: URL or path to a file where to read data from.
        :type input_url: str
        :param inline_metadata: Flag to indicate whether the provided
        metadata is specified inline or is a path to a YAML request.
        :type inline_metadata: bool
        :param asynchronous: Whether to wait for the server to make
        the data available (False) or not (True).
        :type asynchronous: bool
        :param max_attempts: Maximum number of retrials in case the data
        upload fails due to a connection error. It takes the value None
        by default, which means the command will retry until the data
        is uploaded successfully or until the server notifies the request
        has failed.
        :type max_attempts: int
        :param attempt_period: Initial amount of time to wait, in seconds,
        between retrials in case the upload fails due to a connection error.
        This amount, which takes the value 0.1 by default, is increased at a
        rate of 1.2x each iteration (maxing out at 30 seconds).
        :type attempt_period: int
        :returns: None
        """
        situation = "trying to submit an archive request"

        replaced_level = helpers.lower_stream_handler_level(self._logger)
        colls = self.coll_visitor.list()
        helpers.recover_stream_handler_level(self._logger, replaced_level)
        if name not in colls:
            raise ValueError("Collection name '" + name + "' not available.")

        request = copy.deepcopy(metadata)
        if inline_metadata and not isinstance(request, collections.Mapping):
            self._logger.info("Parsing inline metadata...")
            # Preparing an exception in case any mistake is detected
            e = helpers.InvalidRequestError(situation=situation, request=request, reasons=None)
            if request.count('"') != 0 or request.count("'") != 0:
                e.reasons = ["It must not contain quote marks"]
                raise e
            request = request.replace(" ", "")
            request = request.split(",")
            dictionary = {}
            for definition in request:
                definition = definition.split("=")
                if len(definition) != 2:
                    e.reasons = ["It must not contain quote marks"]
                    raise e
                dictionary[definition[0].strip()] = definition[1].strip()
            request = dictionary
        elif not inline_metadata:
            self._logger.info("Reading metadata file...")
            request = os.path.expanduser(request)
            with open(request) as request_file_handler:
                request = yaml.safe_load(request_file_handler)
            if isinstance(request, list):
                if len(request) != 1:
                    e = helpers.PolytopeError(situation=situation)
                    e.description[("Simultaneous upload of multiple " + "requests not yet implemented")]
                    raise e
                request = request[0]

        direct_upload = False
        if input_url.startswith(("http://", "https://")):
            request_url = input_url
        else:
            request_url = ""
            direct_upload = True

        collection = name
        request_object = {"verb": "archive", "request": request, "url": request_url}

        message = "Sending request...\n" + pprint.pformat(request_object)
        self._logger.info(message)

        url = self.config.get_url("upload", collection_id=collection)
        headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}
        method = "post"
        expected_responses = [requests.codes.accepted, requests.codes.other]
        # requests.codes.other is handled explicitly here (allow_redirects = False)
        # in order to avoid automatic redirection and GET to the upload endpoint
        response, response_messages = helpers.try_request(
            method,
            situation=situation,
            expected=expected_responses,
            logger=self._logger,
            url=url,
            headers=headers,
            json=request_object,
            allow_redirects=False,
            skip_tls=self.config.get()["skip_tls"],
        )
        location = response.headers.get("location")
        request_id = location.split("/")[-1]
        if response.status_code == requests.codes.other:
            self._logger.info("Upload request endpoint readily available at uploads/" + request_id)
        elif response.status_code == requests.codes.accepted:
            self._logger.info("Upload request submitted successfully")
        if direct_upload:
            input_file = input_url
            self._logger.info("Please post your data to " + location)
        else:
            input_file = None
            self._logger.info(
                "The Polytope server will pull and list the submitted "
                + "data soon. Please poll "
                + location
                + " for status"
            )
        return self.upload(location, input_file, asynchronous, max_attempts, attempt_period)

    # POST /api/v1/uploads/<request_id>
    # GET /api/v1/uploads/<request_id>
    def upload(self, request_id, input_file=None, asynchronous=False, max_attempts=None, attempt_period=0.1):
        """
        Upload data of a upload request.

        Uploads the data of a previously issued archival request.

        :param request_id: ID or URL of the request which to upload the data for.
        :type request_id: str
        :param input_file: Path to a file where to read the data from. Can be
        None if a URL where to fetch data from has been specified in the
        previous archival request.
        :type input_file: str
        :param asynchronous: Whether to wait for the server to fully process
        the upload data (False) before it is available for retrieval, or not
        (True).
        :type asynchronous: bool
        :param max_attempts: Maximum number of retrials in case the data
        is not immediately found available on the server. It takes the value
        None by default, which means the command will retry until the data
        is uploaded successfully or until the server notifies the request
        has failed.
        :type max_attempts: int
        :param attempt_period: Initial amount of time to wait, in seconds,
        between retrials in case the data is not immediately found available
        on the server. This amount, which takes the value 0.1 by default, is
        increased at a rate of 1.2x each iteration (maxing out at 30 seconds).
        :type attempt_period: int
        :returns: None
        """
        if not max_attempts:
            max_attempts = float("inf")

        situation = "trying to upload data"

        if "://" in request_id:
            url = request_id
            request_id = url.split("/")[-1]
        else:
            url = self.config.get_url("upload", request_id)

        if input_file:
            self._logger.info("Starting data upload...")
            self._logger.info("Loading data from {}...".format(input_file))
            start = time.time()

            input_file = os.path.expanduser(input_file)
            file_path = Path(input_file)
            with Path.open(file_path, "rb") as fid:
                data = fid.read()
            data_checksum = hashlib.md5(data).hexdigest()

            method = "post"
            headers = {
                "Content-Type": "application/x-grib",
                "Authorization": ", ".join(self.auth.get_auth_headers()),
                "X-Checksum": data_checksum,
            }

            start = time.time()
            data_uploaded = False
            attempts = 1
            http_max_attempts = 10
            new_attempt_period = 120
            while not data_uploaded:
                if attempts > http_max_attempts:
                    e = helpers.GivenUpDownloadError(
                        situation=situation, url=url, method=method, request_content=headers, attempts=http_max_attempts
                    )
                    raise e
                attempts += 1

                try:
                    expected_responses = [requests.codes.accepted]
                    response, _ = helpers.try_request(
                        method,
                        situation=situation,
                        expected=expected_responses,
                        logger=self._logger,
                        url=url,
                        headers=headers,
                        data=data,
                        skip_tls=self.config.get()["skip_tls"],
                    )
                    data_uploaded = True
                except requests.exceptions.ConnectionError as e:
                    self._logger.warning("Upload interrupted: " + str(e))
                    self._logger.warning("Sleeping %s seconds" % new_attempt_period)
                    time.sleep(new_attempt_period)
                    self._logger.warning("Retrying upload")

            self._logger.info(
                "Data uploaded successfully. Please poll " + response.headers.get("Location") + " for status"
            )
            elapsed = time.time() - start
            if elapsed:
                self._logger.info(("Upload rate %s/s") % helpers.bytes_to_string(file_path.stat().st_size / elapsed))

        if asynchronous:
            return url

        situation = "waiting for the server to list the uploaded data"
        self._logger.info("Waiting for the server to list the uploaded data...")
        headers = {"Authorization": ", ".join(self.auth.get_auth_headers())}
        method = "get"

        data_ready = False
        status = None
        attempts = 1
        describe_max_attempts = max_attempts
        new_attempt_period = attempt_period
        max_attempt_period = 120
        expected_responses = [requests.codes.ok, requests.codes.accepted]
        while not data_ready:
            if attempts > describe_max_attempts:
                e = helpers.RetriesExceededError(
                    attempts=describe_max_attempts, situation=situation, url=url, method=method, request_content=headers
                )
                raise e

            response, response_messages = helpers.try_request(
                method,
                situation=situation,
                expected=expected_responses,
                logger=self._logger,
                url=url,
                headers=headers,
                skip_tls=self.config.get()["skip_tls"],
            )

            if status != response.json()["status"]:
                status = response.json()["status"]
                self._logger.info("The current status of the " + "request is '" + status + "'")
            if status == "failed":
                e = helpers.PolytopeError(situation)
                e.description = "Upload failed"
                raise e

            data_ready = status == "processed"
            if not data_ready:
                time.sleep(new_attempt_period)
                new_attempt_period *= 1.2
                new_attempt_period = min(new_attempt_period, max_attempt_period)
                attempts = attempts + 1

        self._logger.info("The data has been listed and is available for download")
        return url
