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

import base64
import getpass
import json
import logging
import os
from pathlib import Path

import requests

from . import helpers


class Auth:
    def __init__(self, config, logger=None):
        self.config = config
        self.read_key = None
        if logger:
            self._logger = logger
        else:
            self._logger = logging.getLogger(__name__)

    @property
    def user_key(self):
        return self.config.get()["user_key"]

    @property
    def user_email(self):
        return self.config.get()["user_email"]

    def get_auth_headers(self):
        auth_headers = []
        user_key, user_email, _ = self.fetch_key(login=False)
        if user_key and user_email:
            auth_headers.append("EmailKey %s:%s" % (user_email, user_key))
        if user_key and not user_email:
            auth_headers.append("Bearer %s" % (user_key))
        config = self.config.get()
        bearer_key = config["user_key"]
        if bearer_key:
            auth_headers.append("Bearer %s" % (bearer_key))
        username = config["username"]
        password = config["password"]
        if username and password:
            encode_str = "%s:%s" % (username, password)
            encoded = base64.b64encode(bytes(encode_str, "utf-8")).decode("utf-8")
            auth_headers.append("Basic %s" % encoded)
        return auth_headers

    # POST /api/v1/auth/keys
    def login(self, username=None, password=None, persist=True, key_type="bearer"):
        """
        Log-in (authenticate) a user.

        Authenticate a user with its credentials and obtain a key for use
        in further requests to the server. The supported credentials for
        which a token will be generated are:
          - Polytope plain username and password
          - ECMWF account email (username) and API token (password)

        The user name and obtained key are stored in the Polytope
        configuration folder (configurable with 'polytope set config',
        which is $HOME/.polytope-client/ by default), and are read and used
        in subsequent calls to the Polytope client.

        The credentials in the client configuration folder can be edited
        manually if desired, although not recommended.

        :param username: Name of the user to authenticate
        :type username: str
        :param password: Password of the user to authenticate. If not provided,
        will be read from stdin.
        :type password: str
        :param persist: Whether to set the username as a new configuration
        item in the Polytope client configuration file or not
        :type persist: bool
        :param key_type: Deprecated. Type of authentication key to be
        obtained after authentication. Only 'bearer' supported.
        :type key_type: str
        :returns: None
        """
        situation = "trying to authenticate a user"

        self._logger.info("Authenticating...")

        if not username:
            config = self.config.get()
            username = config["username"]

        if password is None:
            print("Authenticating... please provide the password for the " + "Polytope user " + username + ":")
            password = getpass.getpass()
            self._logger.debug("Password obtained via standard input.")

        if key_type != "bearer":
            raise ValueError("Only 'bearer' supported as key_type.")

        url = self.config.get_url("auth")
        encode_str = "%s:%s" % (username, password)
        headers = {"Authorization": "Basic %s" % base64.b64encode(bytes(encode_str, "utf-8")).decode("utf-8")}
        data = {}
        method = "post"
        expected_responses = [requests.codes.ok]
        response, response_messages = helpers.try_request(
            method,
            situation=situation,
            expected=expected_responses,
            logger=self._logger,
            url=url,
            headers=headers,
            json=data,
            skip_tls=self.config.get()["skip_tls"],
        )
        self._logger.info("User key received successfully" + " (expires " + response_messages["expires"] + ")")
        self.config.set("user_key", response_messages["key"], persist=True)
        self.config.set("username", username, persist=persist)
        return response_messages["key"], username

    def fetch_key(self, login=True):
        # Reads and returns a key and user name present in the Polytope client
        # configuration file, as obtained previously with the command
        # 'cli.py authenticate user'. Crashes if no credentials are present yet.
        # Consistency of key-username can not be guaranteed unless a more
        # complex mechanism for storing keys per user is implemented.
        config = self.config.get()
        if config["user_key"]:
            key = config["user_key"]
            email = config["user_email"]
            return key, email, None
        else:
            if self.read_key and self.read_key_user == config["username"]:
                key = self.read_key
                email = self.read_email
                self._logger.info("Polytope user key found in session cache for user " + config["username"])
            else:
                key_file = Path(config["key_path"])
                try:
                    with open(str(key_file), "r") as infile:
                        info = json.load(infile)
                        key = info.get("user_key", None)
                        email = info.get("user_email", None)

                # TODO: this is messy
                except FileNotFoundError:
                    try:
                        with open(str(Path.home() / ".ecmwfapirc"), "r") as infile:
                            info = json.load(infile)
                            key = info.get("user_key", None)
                            email = info.get("user_email", None)
                    except FileNotFoundError:
                        key = None
                        email = None
                        if login:
                            key, email = self.login(persist=False)
                else:
                    self.read_key = key
                    self.read_email = email
                    self.read_key_user = config["username"]
                    self._logger.info("Key read from " + str(key_file))
            return key, email, config["username"]

    def persist(self, key, email, username=None):
        """
        Write a key in file.

        Writes a key under the Polytope client configuration folder
        (as fixed with 'polytope set config', which is $HOME/.polytope-client
        by default), specifically in the 'keys/username' file.

        Not intended for regular use. See 'polytope login'.

        :param key: Key to be written.
        :type key: str
        :param email: Email to be written.
        :type email: str
        :param username: Name of the user to whom the key belongs.
        :type username: str
        :returns: None
        """
        config = self.config.get()
        if not username:
            username = config["username"]
        os.makedirs(config["key_path"], exist_ok=True)
        key_file = Path(config["key_path"])
        with open(str(key_file), "w", encoding="utf8") as outfile:
            json.dump({"key": key, "email": email}, outfile)
        self.read_key = key
        self.read_email = email
        self.read_key_user = username
        message = "The Polytope user key has been written to " + str(key_file) + "\n"
        self._logger.info(message)

    def erase(self, username=None):
        """
        Remove a key file.

        Removes a key file under the Polytope client configuration folder.

        Not intended for regular use. See 'polytope set credentials'.

        :param username: Name of the user which to remove the credentials for.
        :type username: str
        :returns: None
        """
        config = self.config.get()
        if not username:
            username = config["username"]
        key_path = Path(config["key_path"])
        try:
            os.remove(str(key_path))
            self._logger.info("Credentials removed for " + username)
        except OSError:
            self._logger.warning("No credentials found for " + username)
            pass

    def list(self):
        """
        List existing credentials.

        Shows a list with the existing credentials in the system for the
        Polytope client, which are stored under the polytope configuration
        folder.

        The credentials for the current user (if any) are highlighted.

        :returns: None
        """

        def shadow_key(key, show=4):
            return "**********" + key[(max(0, len(key) - show)) : len(key)]

        message = (
            "Summary of keys. The key in use in the current " + "session (if any) is marked with an arrow (<--).\n\n"
        )
        if self.user_key:
            message += (
                "Session key:\n - username: unspecified | "
                + "email: "
                + self.user_email
                + " | "
                + "key: "
                + shadow_key(self.user_key)
                + " (<--)\n\n"
            )
        config = self.config.get()
        message += "File keys: "
        found_keys = ""
        key_path = Path(config["key_path"])
        if key_path.exists() and key_path.is_dir():
            for key_file in Path(config["key_path"]).iterdir():
                if not key_file.is_file():
                    continue
                with open(str(key_file), "r") as infile:
                    info = json.load(infile)
                    key = info["key"]
                    email = info["email"]
                key = shadow_key(key)
                found_keys += " - username: " + key_file.stem + " | " + "key: " + key + " | " + "email: " + email
                if key_file.stem == config["username"] and not self.user_key:
                    found_keys += " <--"
                found_keys += "\n"
        if found_keys == "":
            message += "None\n"
        else:
            message += "\n" + found_keys
        self._logger.info(message)
