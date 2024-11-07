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
import random
import string
import sys
from traceback import format_tb

from .Admin import Admin
from .Auth import Auth
from .CollectionVisitor import CollectionVisitor
from .Config import Config
from .helpers import PolytopeError, authenticated, wraps
from .RequestManager import RequestManager


class Client:
    """
    This is the main class of the Polytope client API, and the only intended
    for direct use. It exposes methods to perform all possible operations
    against a Polytope server, and operations for user and user credential
    management.
    """

    def __init__(
        self,
        config_path=None,
        address=None,
        port=None,
        username=None,
        key_path=None,
        # execution configuration
        quiet=None,
        verbose=None,
        log_file=None,
        log_level=None,
        # key
        user_key=None,
        user_email=None,
        password=None,
        # https
        insecure=None,
        skip_tls=None,
        # other
        cli=False,
    ):
        """
        Creator method of the Polytope Client.

        Session configuration items can be specified upon instantiation of the
        Polytope client. See help(Client.set_config) for details and defaults.

        :param config_path: Path where to store Polytope client configuration.
        :type config_path: str
        :param address: Address to the Polytope server.
        :type address: str
        :param port: Port of the Polytope server.
        :type port: int
        :param username: Name of the Polytope user to use.
        :type username: str
        :param key_path: Path where to store the Polytope credentials.
        :type key_path: str
        :param quiet: Whether to hide user information messages.
        :type quiet: bool
        :param verbose: Whether to show detailed user information messages.
        :type verbose: bool
        :param log_file: Path where to store user information messages.
        :type log_file: str
        :param log_level: Level of detail of the messages stored in log_file.
        :type log_level: str
        :param user_key: Polytope user key (ECMWF ApiKey) to be used for operations,
        as obtained from the ECMWF Api or via the login method in this client.
        :type user_key: str
        :param user_email: Polytope user email address associated to the user_key.
        :type user_email: str
        :param password: HTTP 'Basic' authentication password to be sent
        together with the configured username. NOTE: this password is not
        intended for regular use. Specifying this Basic authentication password
        is mainly used for authorizing certain operations for administration
        or test users.
        This password is NOT used in the login method when retrieving a
        Polytope user key.
        :type password: str
        :param insecure: Downgrade connection to insecure HTTP.
        :type insecure: bool
        :param skip_tls: Skip TLS certificate verification.
        :type skip_tls: bool
        :param cli: Whether the Client is being created from a CLI or not
        (configured automatically). This will determine whether some messages
        are printed or not by the client.
        :type cli: bool
        """
        # first thing, set up the logger for the API
        logger_id_len = 6
        logger_id = "".join(random.choice(string.ascii_uppercase + string.digits) for _ in range(logger_id_len))
        logger_name = __name__ + "." + logger_id
        self._logger = logging.getLogger(logger_name)

        self._cli = cli

        self.config = Config(
            config_path,
            address,
            port,
            username,
            key_path,
            quiet,
            verbose,
            log_file,
            log_level,
            user_key,
            user_email,
            password,
            insecure=insecure,
            skip_tls=skip_tls,
            logger=self._logger,
            cli=self._cli,
        )

        # Catch and forward Polytope exception messages to logger
        def exception_handler(exception_type, exception, traceback, debug_hook=sys.excepthook):
            if issubclass(exception_type, PolytopeError):
                self._logger.warning("%s: %s" % (exception_type.__name__, exception))
                if traceback:
                    self._logger.debug("".join(format_tb(traceback)))
            else:
                debug_hook(exception_type, exception, traceback)

        sys.excepthook = exception_handler

        self._logger.debug("Creating Polytope client...")
        self.auth = Auth(self.config, logger=self._logger)
        self.admin = Admin(self.config, self.auth, logger=self._logger)
        self.collection_visitor = CollectionVisitor(self.config, self.auth, logger=self._logger)
        self.request_manager = RequestManager(self.config, self.auth, self.collection_visitor, logger=self._logger)

    @wraps(Config.set)
    def set_config(self, *args, **kwargs):
        return self.config.set(*args, **kwargs)

    @wraps(Config.unset)
    def unset_config(self, *args, **kwargs):
        return self.config.unset(*args, **kwargs)

    @wraps(Config.list)
    def list_config(self, *args, **kwargs):
        return self.config.list(*args, **kwargs)

    @wraps(Admin.describe_user)
    def describe_user(self, *args, **kwargs):
        return self.admin.describe_user(*args, **kwargs)

    @wraps(Admin.ping)
    def ping(self, *args, **kwargs):
        return self.admin.ping(*args, **kwargs)

    @wraps(Auth.login)
    def login(self, *args, **kwargs):
        return self.auth.login(*args, **kwargs)

    @wraps(Auth.persist)
    def set_credentials(self, *args, **kwargs):
        return self.auth.persist(*args, **kwargs)

    @wraps(Auth.erase)
    def unset_credentials(self, *args, **kwargs):
        return self.auth.erase(*args, **kwargs)

    @wraps(Auth.list)
    def list_credentials(self, *args, **kwargs):
        return self.auth.list(*args, **kwargs)

    @authenticated
    @wraps(CollectionVisitor.list)
    def list_collections(self, *args, **kwargs):
        return self.collection_visitor.list(*args, **kwargs)

    @authenticated
    @wraps(CollectionVisitor.describe)
    def describe_collection(self, *args, **kwargs):
        return self.collection_visitor.describe(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.retrieve)
    def retrieve(self, *args, **kwargs):
        return self.request_manager.retrieve(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.archive)
    def archive(self, *args, **kwargs):
        return self.request_manager.archive(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.list)
    def list_requests(self, *args, **kwargs):
        return self.request_manager.list(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.describe)
    def describe_request(self, *args, **kwargs):
        return self.request_manager.describe(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.revoke)
    def revoke(self, *args, **kwargs):
        return self.request_manager.revoke(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.download)
    def download(self, *args, **kwargs):
        return self.request_manager.download(*args, **kwargs)

    @authenticated
    @wraps(RequestManager.upload)
    def upload(self, *args, **kwargs):
        return self.request_manager.upload(*args, **kwargs)
