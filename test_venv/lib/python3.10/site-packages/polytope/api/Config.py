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

import getpass
import logging
import os
import pprint
import urllib.parse
from http.client import HTTPConnection
from pathlib import Path

import yaml

from . import helpers


class Config:
    def __init__(
        self,
        config_path=None,
        address=None,
        port=None,
        username=None,
        key_path=None,
        quiet=None,
        verbose=None,
        log_file=None,
        log_level=None,
        user_key=None,
        user_email=None,
        password=None,
        insecure=None,
        skip_tls=None,
        logger=None,
        cli=False,
    ):
        # hard-coded defaults are not specified in the __init__ header
        # so that session configuration specified in the headers is not
        # directly merged into the hard-coded configuration before the file
        # configuration is applied

        # __init__ collects and merges client configuration from five sources,
        # in the following order (subsequent layers override configuration
        # already present in the previous layers):
        #  - hard-coded defaults
        #  - system-wide configuration file
        #  - configuration file
        #  - env variables
        #  - session ad hoc configuration

        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)
        self._cli = cli
        self.file_config_items = [
            "address",
            "port",
            "username",
            "key_path",
            "quiet",
            "verbose",
            "log_file",
            "log_level",
            "user_key",
            "user_email",
            "password",
            "insecure",
            "skip_tls",
        ]

        # Reading session configuration
        config = locals()
        config.pop("self")
        config.pop("config_path")
        config.pop("logger")
        config.pop("cli")
        self.session_config = helpers.process_config(config)

        # Default polytope client environment configuration
        config = {}
        config["address"] = "polytope.ecmwf.int"
        config["port"] = None
        config["username"] = getpass.getuser()
        config["key_path"] = None  # this default may be readjusted later
        # according to the config_path
        config["quiet"] = False
        config["verbose"] = False
        config["log_file"] = None
        config["log_level"] = "DEBUG"
        config["user_key"] = None
        config["user_email"] = None
        config["password"] = None
        config["insecure"] = False
        config["skip_tls"] = False
        self.default_config = config

        # Reading system-wide file configuration
        system_config_path = Path("/etc/polytope-client/config.yaml")
        self.system_file_config = helpers.read_config(system_config_path)

        # Reading file configuration
        if not config_path:
            config_path = os.environ.get("POLYTOPE_CONFIG_PATH")
        if config_path:
            config_path = Path(os.path.expanduser(config_path))
            self.config_path = config_path
        else:
            self.config_path = Path.home() / ".polytope-client"
        self.default_config["key_path"] = Path.home() / ".polytopeapirc"
        self.file_config = helpers.read_config(self.config_path)

        # Reading env var configuration
        def fun(x):
            return "POLYTOPE_" + x.upper()

        env_var_config = {}
        for var in self.file_config_items:
            val = os.environ.get(fun(var))
            if val:
                env_var_config[var] = val
        self.env_var_config = env_var_config

        self.update_loggers()

        message = "Gathered Polytope client configuration:\n"
        message += pprint.pformat(self.get())
        self._logger.debug(message)

    def get_url(self, endpoint, request_id=None, collection_id=None):
        # This function generates an HTTP URL pointing to the API exposed by a
        # Polytope frontend instance. The IP and port are read from the
        # configuration file (after being set manually by the user, or using the
        # 'polytope config' command), or set to the default 127.0.0.1:5678 if not
        # configured.
        config = self.get()
        valid_endpoints = ["api_root", "auth", "users", "requests", "download", "upload", "ping", "collections"]
        if endpoint not in valid_endpoints:
            raise ValueError("Unrecognized frontend endpoint requested.")
        if endpoint == "api_root":
            suffix = ""
        elif endpoint == "auth":
            suffix = "/auth/keys"
        elif endpoint == "users":
            suffix = "/user"
        elif endpoint == "requests":
            suffix = "/requests"
            if request_id:
                suffix += "/" + request_id
            elif collection_id:
                suffix += "/" + collection_id
        elif endpoint == "collections":
            suffix = "/collections"
        elif endpoint == "download":
            suffix = "/downloads"
            if request_id:
                suffix += "/" + request_id
        elif endpoint == "upload":
            suffix = "/requests"
            if collection_id:
                suffix += "/" + collection_id
            elif request_id:
                suffix = "/uploads/" + request_id
        elif endpoint == "ping":
            suffix = "/test"
        else:
            raise helpers.BugError

        url = config["address"]

        # Add default scheme 'https://' if it was not specified
        if not url.startswith(("http://", "https://")) and "://" not in url:
            url = "https://" + url

        # Split URL and validate each component
        parsed_url = urllib.parse.urlsplit(url)

        scheme = parsed_url.scheme
        if scheme not in ("http", "https"):
            raise ValueError("Unrecognized URL scheme {}".format(scheme))

        if scheme == "https" and config["insecure"]:
            scheme = "http"

        if scheme == "http" and not config["insecure"]:
            raise ValueError("Cannot use http without insecure flag")

        if not parsed_url.hostname:
            raise ValueError("URL {} could not be parsed".format(url))

        # Adopt the port from URL if it exists, else read config
        port = parsed_url.port or config["port"]

        if port is None:
            port = 80 if scheme == "http" else 443

        # Create the full path and reconstruct the URL
        path = os.path.join(parsed_url.path + "/api/v1" + suffix)
        url = urllib.parse.urlunsplit((scheme, parsed_url.hostname + ":" + str(port), path, None, None))

        return url

    def get(self):
        # gathers, merges and returns all configuration, as detailed in the
        # documentation of __init__
        config = {}
        config.update(self.default_config)
        config.update(self.system_file_config)
        config.update(self.file_config)
        config.update(self.env_var_config)
        config.update(self.session_config)
        special_file_priority = ["quiet", "verbose", "insecure", "skip_tls"]
        for item in special_file_priority:
            if item in self.session_config and not self.session_config[item]:
                if item in self.system_file_config:
                    config[item] = self.system_file_config[item]
                if item in self.file_config:
                    config[item] = self.file_config[item]

        booleans = ["quiet", "verbose", "insecure", "skip_tls"]
        for item in booleans:
            if isinstance(config[item], str):
                config[item] = config[item].lower() in ["true", "1"]

        return config

    def update_loggers(self):
        config_dict = self.get()

        # polytope loggers
        if config_dict["verbose"]:
            stream_log_level = "DEBUG"
        else:
            stream_log_level = "INFO"
        helpers.set_stream_handler(self._logger, config_dict["quiet"], stream_log_level)
        helpers.set_file_handler(self._logger, config_dict["log_file"], config_dict["log_level"])

        # requests loggers
        # actually, the requests module doesn't implement logging loggers
        # the urllib3 module does
        # and the http.client just prints information out
        logger = logging.getLogger("urllib3")
        logger.setLevel(logging.DEBUG)
        quiet = config_dict["quiet"]
        log_file = config_dict["log_file"]
        if not config_dict["verbose"]:
            quiet = True
            HTTPConnection.debuglevel = 0
        else:
            if not quiet:
                HTTPConnection.debuglevel = 1
        if config_dict["log_level"] != "DEBUG":
            log_file = None
        helpers.set_stream_handler(logger, quiet, "DEBUG")
        helpers.set_file_handler(logger, log_file, "DEBUG")

    def list(self):
        """
        Show Polytope client configuration.

        Lists the current Polytope client configuration, as stored in the
        Polytope client configuration file ($HOME/.polytope-client by
        default).

        For each configuration item, its name and value are shown. Also,
        its origin is shown wrapped in brackets. The possible origins of
        a configuration item can be 'default', 'system file', 'file',
        'env var' or 'session'. See 'polytope set config' for more
        information.

        :returns: None
        """
        config = {}
        origins = {}
        for k, v in self.default_config.items():
            config[k] = v
            origins[k] = "default"
        for k, v in self.system_file_config.items():
            config[k] = v
            origins[k] = "system file"
        for k, v in self.file_config.items():
            config[k] = v
            origins[k] = "file"
        for k, v in self.env_var_config.items():
            config[k] = v
            origins[k] = "env var"
        for k, v in self.session_config.items():
            config[k] = v
            origins[k] = "session"

        special_file_priority = ["quiet", "verbose", "insecure", "skip_tls"]
        for item in special_file_priority:
            if item in self.session_config and not self.session_config[item]:
                if item in self.system_file_config:
                    config[item] = self.system_file_config[item]
                    origins[item] = "system file"
                if item in self.file_config:
                    config[item] = self.file_config[item]
                    origins[item] = "file"

        message = "Found configuration items:\n"
        for k in config:
            print_value = config[k]
            if k == "password" and config[k]:
                print_value = "**hidden**"
            message += " - ({}) {}: {}\n".format(origins[k], k, print_value)
        if len(self.system_file_config) > 0:
            message += "The system-wide configuration file " + "is /etc/polytope-client/config.json\n"
        message += "The configuration source directory used in this session " + "is " + str(self.config_path)

        self._logger.info(message)

    def set(self, key, value, persist=False):
        """
        Configure the Polytope client.

        Sets a Polytope client configuration item, such as the IP address
        or port where the Polytope server frontend is exposed, as well as a
        user name to be used for the next operations with the Polytope server.
        See below for a complete list of configurable items.

        (Not relevant to CLI users): The new configuration item is added to
        the session configuration (in order for the new value to take effect
        over potential previous session configuration values for the same
        item) and, if 'persist = True' (always the case when used from the
        CLI), it is as well stored in the Polytope client configuration file
        ($HOME/.polytope-client/config.yaml by default).

        During execution, whenever the Polytope client does not find a value
        in the configuration file for any configuration item, a system-wide
        configuration file (/etc/polytope-client/config.yaml) is first
        checked to find a value and, if not found, a library-internal fixed
        value is used.

        Configuration items in the configuration file can be overridden with
        environment variables (e.g. POLYTOPE_PORT, POLYTOPE_VERBOSE, ...)
        specified before running the API or CLI.

        When using the Polytope client API, upon creation of the client
        (i.e. when instantiating the Client class), additional session
        configuration values can be specified via the creator or via
        environment variables. These values will take priority over any
        library-defaults, file configurations or environment variables.

        The configuration items 'quiet' and 'verbose' are special.
        The Polytope CLI specifically sets them to True or False (depending
        on whether the CLI user specified the --quiet or --verbose flags) when
        instantiating the Client class, and hence these items show up as
        session configurations when queried via 'polytope list config'.
        However, if these items are set in the configuration file, and the
        session --quiet or --verbose flags have not been specified, the file
        values will take priority over the session configuration values. In
        that case, the origin of the configuration item in 'polytope list
        config' will show as '(file)'.

        The available configurable items, their library-default values and
        their meaning are listed below:

        address: polytope.ecmwf.int
        URL or IP address to the Polytope server frontend.

        port: 80
        Port used by the Polytope server frontend.

        username: host system user name
        Name of the Polytope user to use for subsequent client operations.
        This username is used to:
         - log in the system and name the obtained credential (key)
         - easily identify the key to be used in subsequent client operations
        This configuration item does not have an effect if a session key has
        been specified.

        key_path: config_path/keys
        Path where the user credentials are stored.

        quiet: False
        Whether to hide user information messages or not.

        verbose: False
        Whether to show detailed information of the progress or not.

        log_file: None
        File where to store the user information messages.

        log_level: DEBUG
        Level of detail of the log messages stored in the log_file. Accepts
        any Python logging level (WARNING, INFO, DEBUG, ...).

        user_key: None
        Polytope user key

        user_email: None
        Polytope user email associated to the user_key.

        password: None
        HTTP Basic authentication password. Strongly recommended to specify this
        configuration item only via the environment variable POLYTOPE_PASSWORD
        or manually in the Polytope configuration file.

        :param key: Name of the configuration item to set.
        :type key: str
        :param value: Value for the configuration item.
        :type value: str
        :param persist: Whether to apply the change in the Polytope client
        configuration or not (default).
        :type persist: bool
        :returns: None
        """
        if key not in self.file_config_items:
            raise ValueError("Invalid configuration key provided (" + key + ")")

        print_value = value
        if key == "password" and value:
            print_value = "**hidden**"

        self.session_config[key] = value
        self.update_loggers()

        if not persist:
            if not self._cli:
                message = (
                    "Successfully updated the following configuration "
                    + "item for the current Polytope client session:\n"
                )
                message += " - {}: {}\n".format(key, print_value)
                self._logger.info(message)
            return

        config = self.file_config
        config[key] = value
        helpers.convert_back(config)
        helpers.validate_config(config)
        self.file_config = config
        os.makedirs(str(self.config_path), exist_ok=True)
        with open(str(self.config_path / "config.yaml"), "w", encoding="utf8") as outfile:
            yaml.dump(config, outfile, default_flow_style=False, allow_unicode=True)
        message = (
            "Successfully updated the following configuration " + "item in the Polytope client configuration file:\n"
        )
        message += " - {}: {}\n".format(key, print_value)
        self._logger.info(message)
        if key == "user_key":
            message = (
                "A session key has been specified. The "
                + "specified 'username' ("
                + self.get()["username"]
                + ") will be ignored."
            )
            self._logger.info(message)

    def unset(self, key, persist=False):
        """
        Remove Polytope client configurations.

        Removes a Polytope client configuration item.

        (Not relevant to CLI users): The item is removed from the current
        session configuration if present and, if 'persist = True' (always
        the case when used from the CLI), it is removed as well from the
        Polytope client configuration file.

        See 'polytope set config' for more information.

        :param key: Name of the configuration item to be removed. Can take
        the value 'all' to remove all file configuration items.
        :type key: str
        :param persist: Whether to apply the change in the Polytope client
        configuration or not (default).
        :type persist: bool
        :returns: None
        """
        if key == "all":
            self.session_config = {}
            self._logger.info("Configuration wiped.")

            if not persist:
                return

            config_dir = self.config_path
            try:
                os.remove(str(config_dir / "config.yaml"))
                self._logger.debug("Deleted " + str(config_dir / "config.yaml"))
            except OSError:
                self._logger.debug("Configuration file not found.")
                pass
            self.file_config = {}
            return

        if key not in self.file_config_items:
            raise ValueError("Invalid configuration key provided (" + key + ")")

        if key in self.session_config:
            del self.session_config[key]

        message = (
            "Successfully removed the following configuration " + "item for the Polytope client:\n  - " + key + "\n"
        )
        self._logger.info(message)
        self.update_loggers()

        if not persist:
            return

        if key not in self.file_config:
            self._logger.info("Configuration item '" + key + "' not currently present in the configuration file.")
            return

        del self.file_config[key]
        os.makedirs(str(self.config_path), exist_ok=True)
        with open(str(self.config_path / "config.yaml"), "w", encoding="utf8") as outfile:
            yaml.dump(self.file_config, outfile, default_flow_style=False, allow_unicode=True)
