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

from functools import wraps

import click
from docstring_parser import parse

from ...api.Client import Client


def user_configurable(function):
    # in order to add a new regular user configurable parameter to Polytope,
    # the following source files have to be adapted:
    #  - cli/binders/helpers.py (both functions in this file)
    #  - cli/binders/config.py
    #  - api/helpers.py (configure() and possibly convert_back())
    #  - api/Client.py (__init__())
    #  - api/Config.py (__init__() and persist())
    #  - api/config_schema.json
    doc = parse(Client.__init__.__doc__)

    # special user configurable options
    @click.option("config_path", "-c", "--config-path", help=doc.params[0].description)
    # regular user configurable options
    @click.option("address", "-a", "--address", help=doc.params[1].description)
    @click.option("port", "-p", "--port", help=doc.params[2].description)
    @click.option("username", "-u", "--username", help=doc.params[3].description)
    @click.option("key_path", "-K", "--key-path", help=doc.params[4].description)
    @click.option("quiet", "-q", "--quiet", help=doc.params[5].description, is_flag=True)
    @click.option("verbose", "-v", "--verbose", help=doc.params[6].description, is_flag=True)
    @click.option("log_file", "--log-file", help=doc.params[7].description)
    @click.option(
        "log_level",
        "--log-level",
        help=doc.params[8].description,
    )
    # key option
    @click.option("user_key", "-k", "--user-key", help=doc.params[9].description)
    @click.option("user_email", "--user-email", help=doc.params[10].description)
    @click.option("password", "--password", help=doc.params[11].description)
    @click.option("insecure", "--insecure", default=False, help=doc.params[12].description, is_flag=True)
    @click.option("skip_tls", "--skip-tls", default=False, help=doc.params[13].description, is_flag=True)
    @wraps(function)
    def decorated(**kwargs):
        return function(**kwargs)

    return decorated


def filter_session_args(**kwargs):
    all_args = {**kwargs}
    session_args = {"cli": True}
    session_arg_names = [
        "config_path",
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
    for name in session_arg_names:
        session_args[name] = all_args[name]
        all_args.pop(name)
    return session_args, all_args
