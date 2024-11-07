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

import json
import logging
import os
import socket
import time
from inspect import signature
from pathlib import Path

import jsonschema
import requests
import yaml

# Exceptions
###


class PolytopeError(Exception):
    """Base class for exceptions in the polytope module."""

    def __init__(self, situation=None):
        self.situation = situation
        self.description = None

    def __str__(self):
        message = "Polytope error"
        if self.situation:
            message += "\nSituation: " + self.situation
        if self.description:
            message += "\nDescription: " + self.description
        return message


class HTTPRequestError(PolytopeError):
    """Docu missing."""

    def __init__(self, url, method, request_content=None, **kwargs):
        super().__init__(**kwargs)
        self.description = "HTTP request error."
        self.url = url
        self.method = method
        self.request_content = request_content

    def __str__(self):
        message = super().__str__()
        message += "\nURL: " + self.url
        message += "\nHTTP method: " + self.method.upper()
        if self.request_content:
            message += "\nRequest header/body contents:\n"
            content = self.request_content
            if content.get("headers"):
                if "Authorization" in content["headers"]:
                    value = content["headers"]["Authorization"]
                    auths = value.split(", ")
                    filtered = []
                    for auth in auths:
                        kind = auth.split(" ")[0]
                        key = auth.split(" ")[1]
                        show = 4
                        key = "**********" + key[(max(0, len(key) - show)) : len(key)]
                        filtered.append("%s %s" % (kind, key))
                    content["headers"]["Authorization"] = ", ".join(filtered)
            message += str(content)
        return message


class HTTPResponseError(HTTPRequestError):
    """Raised when an unexpected response (according to the system design schema)
    is received."""

    def __init__(self, response, expected=None, **kwargs):
        super().__init__(**kwargs)
        self.description = "HTTP error."
        self.response = response
        self.expected = expected
        self.response_title = None
        self.messages = None

    def __str__(self):
        message = super().__str__()
        if self.expected:
            expected_str = list(map(lambda x: str(x), self.expected))
            message += "\nExpected responses: " + ", ".join(expected_str)
        message += "\nReceived response: " + self.response_title
        if "message" in self.messages:
            message += "\nSummarized response:\n%s\n" % self.messages["message"]
        message += "\nDetails:\n"
        message += "\n  - ".join(self.messages)
        return message


class ExpiredCredentialsError(HTTPResponseError):
    """Docu missing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)


class GivenUpRequestError(HTTPRequestError):
    """Docu missing."""

    def __init__(self, attempts, **kwargs):
        super().__init__(**kwargs)
        self.attempts = attempts
        self.description = (
            "Stopped attempting HTTP request after "
            + "exceeding the maximum of "
            + str(self.attempts)
            + " failed attempts (caused by connection "
            + "errors or other HTTP errors where retrial is sensible)."
        )


class GivenUpDownloadError(HTTPRequestError):
    """Docu missing."""

    def __init__(self, attempts, **kwargs):
        super().__init__(**kwargs)
        self.description = (
            "Stopped attempting to download the data after "
            + "exceeding the maximum of "
            + str(attempts)
            + " failed attempts (data not ready on the server)."
        )


class RetriesExceededError(HTTPRequestError):
    """Docu missing."""

    def __init__(self, attempts, **kwargs):
        super().__init__(**kwargs)
        self.attempts = attempts
        self.description = "Data not ready for download after " + str(attempts) + " retries. Check back later."


class InvalidRequestError(PolytopeError):
    """Docu missing."""

    def __init__(self, request, reasons=None, **kwargs):
        super().__init__(**kwargs)
        self.description = "Invalid request."
        self.request = request
        self.reasons = reasons

    def __str__(self):
        message = super().__str__()
        if self.reasons:
            message += "\nReasons:\n  - "
            message += "\n  - ".join(self.reasons)
        message += "\nProvided request:\n"
        message += str(self.request)
        return message


class BugError(PolytopeError):
    """Docu missing."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.description = (
            "Bug encountered in the Polytope client. "
            + "Please, enable the verbose mode (polytope set config verbose "
            + "True), run your command again, and contact "
            + "software.support@ecmwf.int providing the commands to "
            + "reproduce the situation and the full Python traceback shown "
            + "alongside the error message."
        )


# Decorators
###

default_assign = ["__doc__", "__annotations__", "__dict__", "__signature__", "__qualname__"]
default_update = ["__name__"]


def wraps(*args, assign=default_assign, update=default_update):
    def wrapper(fun):
        def decorated(self, *args, **kwargs):
            return fun(self, *args, **kwargs)

        wrapped = [*args][0]
        for attr in assign:
            if attr == "__signature__":
                val = signature(wrapped)
            else:
                val = getattr(wrapped, attr)
            setattr(decorated, attr, val)
        for attr in update:
            val = getattr(fun, attr)
            setattr(decorated, attr, val)
        return decorated

    return wrapper


def authenticated(method):
    @wraps(method, assign=default_assign + default_update, update=[])
    def decorated(self, *args, **kwargs):
        auth_headers = self.auth.get_auth_headers()
        if len(auth_headers) < 1:
            e = PolytopeError(situation=("trying to run a Polytope command " + "which requires authentication"))
            e.description = (
                "No authentication credentials found. "
                + "Please login to Polytope with the login command, "
                + "or provide a Polytope key and email, a Polytope bearer key, "
                + "or basic authentication Polytope user credentials via client "
                + "configuration or environment variables."
            )
            raise e
        # try:
        return method(self, *args, **kwargs)
        # except ExpiredCredentialsError:
        #    self._logger.warning('Expired credentials. Proceeding to ' +
        #        'authenticate and request a new key.')
        #    self.auth.login(persist = False)
        #    return method(self, *args, **kwargs)

    return decorated


# Logging-related helper functions
###


class LogFormatter(logging.Formatter):
    def __init__(self, prettyprint):
        super(LogFormatter, self).__init__()
        self.prettyprint = prettyprint
        self.indexable_fields = {"request_id": str}
        self.indent = None
        if self.prettyprint:
            self.indent = 2

    def format(self, record):
        msg = super(LogFormatter, self).format(record)

        result = {}
        result["src"] = str(record.name)
        result["lvl"] = str(record.levelname)
        result["pth"] = str("{}:{}".format(record.pathname, record.lineno))
        result["msg"] = str(msg)
        result["pid"] = str(record.process)
        result["host"] = str(socket.getfqdn())
        result["date"] = str(record.created)

        # log accepts extra={} args to eg. logging.debug
        # if the extra arguments match known indexable_fields these are
        # added to the log
        # these strongly-typed fields can be used for indexing of logs

        for name, typ in self.indexable_fields.items():
            if not hasattr(record, name):
                continue

            val = getattr(record, name)
            if isinstance(val, typ):
                result[name] = val
            else:
                raise TypeError(
                    "Extra information with key {} is \
                     expected to be of type {}".format(
                        name, typ
                    )
                )

        return json.dumps(result, indent=self.indent, sort_keys=True)


def set_stream_handler(logger, quiet, log_level):
    old_handler = None
    for handler in logger.handlers:
        if type(handler).__name__ == "StreamHandler":
            old_handler = handler
            break
    if old_handler:
        logger.removeHandler(old_handler)

    if not quiet:
        new_handler = logging.StreamHandler()
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % log_level)
        new_handler.setLevel(numeric_level)
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", "%Y-%m-%d %H:%M:%S")
        new_handler.setFormatter(formatter)
        new_handler._polytope_handler_type = "stream"
        logger.addHandler(new_handler)


def set_file_handler(logger, log_file, log_level):
    old_handler = None
    for handler in logger.handlers:
        if type(handler).__name__ == "FileHandler":
            old_handler = handler
            break
    if old_handler:
        logger.removeHandler(old_handler)

    if log_file:
        new_handler = logging.FileHandler(log_file)
        numeric_level = getattr(logging, log_level.upper(), None)
        if not isinstance(numeric_level, int):
            raise ValueError("Invalid log level: %s" % log_level)
        new_handler.setLevel(numeric_level)
        formatter = LogFormatter(True)
        new_handler.setFormatter(formatter)
        logger.addHandler(new_handler)


def lower_stream_handler_level(logger):
    warning_level = getattr(logging, "WARNING")
    info_level = getattr(logging, "INFO")
    replaced_level = None
    handlers = logger.handlers
    for handler in handlers:
        if type(handler).__name__ == "StreamHandler":
            if handler.level == info_level:
                replaced_level = handler.level
                handler.setLevel(warning_level)
            break
    return replaced_level


def recover_stream_handler_level(logger, replaced_level):
    if replaced_level:
        handlers = logger.handlers
        for handler in handlers:
            if type(handler).__name__ == "StreamHandler":
                handler.setLevel(replaced_level)
                break


# Helper functions of the Polytope client
###


def bytes_to_string(amount, basic_unit="B"):
    for unit in ["", "Ki", "Mi", "Gi", "Ti", "Pi", "Ei", "Zi"]:
        if abs(amount) < 1024.0:
            return "%.1f%s%s" % (amount, unit, basic_unit)
        amount = amount / 1024.0
    return "%.1fYi%s" % (amount, basic_unit)


def tidy_click_config(dictionary):
    # when click returns the values for the client configuration parameters
    # (available in all commands), they can have a value specified by the
    # user, the special value 'delete', or no value (None). All these
    # parameters are forwarded from the CLI to the API, and here the API
    # is removing those parameters with a None value, so that it is
    # disregarded in all further operations in the API.
    return {k: v for k, v in dictionary.items() if v is not None}


def convert_back(dictionary):
    # e.g. port is being received as a string from the CLI. Here we convert
    # it to an integer before the schema validation further below.
    for k, v in dictionary.items():
        if k == "port":
            dictionary[k] = int(v)
        elif k in ["quiet", "verbose", "insecure", "skip_tls"]:
            if isinstance(v, bool):
                # The 'convert_back' function is used in two similar but
                # different scenarios:
                #  - to process the 'new_*' params (i.e. new_quiet and
                #    new_verbose) specified via the CLI call to
                #    'polytope config' (for which the 'new_' prefix is
                #    removed) or the API call to Config.set.
                #    In these cases their values come as strings and need
                #    to be converted back to bool.
                #  - to process the common configuration parameters
                #    (i.e. quiet and verbose) in all calls to the CLI or
                #    when initializing the API Client().
                #    In these cases their values come as booleans and do
                #    not need to be converted.
                continue
            if v == "True":
                dictionary[k] = True
            elif v == "False":
                dictionary[k] = False
            else:
                raise ValueError(
                    "When calling 'polytope config set', "
                    + "the values for the keys 'quiet', 'verbose', "
                    + "'insecure' and 'skip_tls' "
                    + "can only take 'True' or 'False' "
                    + "(the same applies if calling "
                    + "polytope.api.Client.set_config or "
                    + "polytope.api.Config.set)."
                )
        elif k == "key_path":
            dictionary[k] = os.path.expanduser(v)


def validate_config(dictionary):
    # validates a configuration against the schema specification provided
    # in the Polytope client module.
    schema_file = Path(__file__).parent / "config_schema.json"
    with open(str(schema_file), "r") as schema_file_handler:
        schema = json.loads(schema_file_handler.read())
    jsonschema.validate(dictionary, schema)


def process_config(config):
    config = tidy_click_config(config)
    convert_back(config)
    validate_config(config)
    return config


def read_config(config_path):
    # This function reads the configuration parameters set in the Polytope
    # client configuration file, if exists, at the specified location, and
    # returns it as a python dictionary.
    found_config = {}

    config_file_path = str(config_path / "config.yaml")
    if os.path.isfile(config_file_path):
        with open(config_file_path, "r") as config_file:
            try:
                found_config = yaml.safe_load(config_file)
                if not found_config:
                    found_config = {}
            except Exception as e:
                message = "Error while reading the configuration file at " + config_file_path + ":\n"
                message += str(e)
                raise e
    try:
        validate_config(found_config)
    except Exception as e:
        message = "Invalid configuration found at " + config_file_path
        message += str(e)
        raise e

    return found_config


def process_response(response, situation, url, method, stream, request_content, expected):
    # This function ingests an HTTP response (as yield by the 'requests' python
    # module) and performs common checks and operations needed for all responses
    # received by the Polytope client. Returns a 'title' with the kind of response
    # received, and a dictionary of ready-to-print 'response_messages' with
    # all relevant textual response messages received.
    e = HTTPResponseError(
        situation=situation,
        url=url,
        method=method,
        request_content=request_content,
        response=response,
        expected=expected,
    )

    response_type = int(round(response.status_code, -2))
    response_types_str = {
        100: "INFORMATION",
        200: "SUCCESS",
        300: "REDIRECTION",
        400: "CLIENT ERROR",
        500: "SERVER ERROR",
    }
    response_type_str = response_types_str.get(response_type, "INVALID RESPONSE CODE")
    response_title = response_type_str + " (" + str(response.status_code) + ")"

    content_type = response.headers.get("Content-Type")
    if content_type == "application/x-grib":
        message = "**skipped**"
        content_length = response.headers.get("Content-Length")
        if content_length:
            message += " (length of data content is %s bytes)" % content_length
        response_messages = {"data": message}
    else:
        try:
            response_messages = response.json()
            # the following lines force the response to always be a dictionary, for code simplicity
            if not isinstance(response_messages, dict):
                if not isinstance(response_messages, list):
                    response_messages = [response_messages]
                new_response_messages = {}
                for i in range(len(response_messages)):
                    new_response_messages[("unnamed_message_" + str(i))] = str(response_messages[i])
                response_messages = new_response_messages
        except Exception:
            response_messages = {"error": response.reason}
            if response.text.find("<!--") >= 0:
                response_messages["log"] = response.text.split("<!--")[-1].split("-->")[0]
        if stream:
            response.close()

    e.response_title = response_title
    e.messages = response_messages

    if response.status_code >= 400 or response_type_str == "INVALID RESPONSE CODE":
        response_values = ["(no response messages received)"]
        if len(response_messages) > 0:
            response_values = list(response_messages.values())
            response_values = ["(empty message)" if x is None else x for x in response_values]
        response_messages = response_values
        e.messages = response_messages
        if response_type_str == "INVALID RESPONSE CODE":
            e.description += " Invalid HTTP response received from the server."
        else:
            e.description = "HTTP " + e.response_title
        if response.status_code == 401 and "expired" in response_messages[0]:
            e.__class__ = "ExpiredCredentialsError"
        raise e
    elif response.status_code not in expected:
        e.description = "Unexpected HTTP response from the server."
        raise e

    return response_title, response_messages


def try_request(method, situation, expected, logger, stream=False, skip_tls=False, **kwargs):
    url = kwargs.get("url", None)
    verify = not skip_tls
    request_content = {"headers": kwargs.get("headers", None), "json": kwargs.get("json", None)}

    def retriable(code):
        if code in [
            requests.codes.internal_server_error,
            requests.codes.bad_gateway,
            requests.codes.service_unavailable,
            requests.codes.gateway_timeout,
            requests.codes.too_many_requests,
            requests.codes.request_timeout,
        ]:
            return True
        return False

    attempt = 1
    max_attempts = 10
    sleep = 120
    success = False
    while attempt <= max_attempts:
        try:
            method_to_call = getattr(requests, method)
            logger.debug("Polytope client attempting HTTP " + method.upper() + " " + url + "\n" + str(request_content))
            response = method_to_call(**kwargs, verify=verify, stream=stream)
        except requests.exceptions.ConnectionError as e:
            response = None
            message = "Recovering from connection error."
            message += "\n" + str(e)
            logger.warning(message)

        if response is not None:
            if retriable(response.status_code):
                message = (
                    "Recovering from HTTP error ("
                    + str(response.status_code)
                    + ": "
                    + requests.status_codes._codes[response.status_code][0]
                    + ")"
                )
                logger.warning(message)
            else:
                success = True
                break

        logger.info("Attempt " + str(attempt) + " of " + str(max_attempts))
        logger.info("Next retry in " + str(sleep) + " seconds")
        attempt = attempt + 1
        time.sleep(sleep)

    if not success:
        e = GivenUpRequestError(
            situation=situation,
            url=kwargs.get("url"),
            method=method,
            request_content=request_content,
            attempts=max_attempts,
        )
        logger.warning("Maximum HTTP request retries reached")
        raise e

    response_title, response_messages = process_response(
        response, situation, url, method, stream, request_content, expected
    )

    logger.debug("Polytope client received HTTP " + response_title)

    return response, response_messages
