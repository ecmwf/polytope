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

import click
from docstring_parser import parse

from ...api.Client import Client
from . import helpers

# login
doc = parse(Client.login.__doc__)


@click.command(
    short_help=doc.short_description,
    help=(doc.params[0].arg_name.upper() + ": " + doc.params[0].description + "\n\n" + doc.long_description),
)
# although the API method Auth.login accepts a 'username' parameter
# in first place, we don't send it here, as the login method will
# take the either username specified in the configuration file or
# the username specified via the global polytope session configuration
# (which can be specified via --username). In other words, if the
# user wants to authenticate a specific user, they can do so by
# adding the parameter --username other_username to the polytope login
# call, which is forwarded as session configuration in the creation
# of the Client() object below.
@click.argument("user_name", type=str, required=False)
@click.option("pass_word", "--login-password", help=doc.params[1].description)
@click.option("key_type", "--key-type", default="bearer", help=doc.params[2].description)
@helpers.user_configurable
def login(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    other_args["username"] = other_args["user_name"]
    del other_args["user_name"]
    other_args["password"] = other_args["pass_word"]
    del other_args["pass_word"]
    Client(**session_args).login(**other_args)


# set_credentials
doc = parse(Client.set_credentials.__doc__)


@click.command(
    short_help=doc.short_description,
    help=(
        doc.params[0].arg_name.upper()
        + ": "
        + doc.params[0].description
        + "\n\n"
        + doc.params[1].arg_name.upper()
        + ": "
        + doc.params[1].description
        + "\n\n"
        + doc.params[2].arg_name.upper()
        + ": "
        + doc.params[2].description
        + "\n\n"
        + doc.long_description
    ),
)
@click.argument("user_key", type=str)
@click.argument("user_email", type=str)
@click.argument("user_name", type=str, required=False)
@helpers.user_configurable
def set(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    other_args["username"] = other_args["user_name"]
    del other_args["user_name"]
    Client(**session_args).set_credentials(**other_args)


# unset_credentials
doc = parse(Client.unset_credentials.__doc__)


@click.command(
    short_help=doc.short_description,
    help=(doc.params[0].arg_name.upper() + ": " + doc.params[0].description + "\n\n" + doc.long_description),
)
@click.argument("user_name", type=str, required=False)
@helpers.user_configurable
def unset(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    other_args["username"] = other_args["user_name"]
    del other_args["user_name"]
    Client(**session_args).unset_credentials(**other_args)


# list credentials
doc = parse(Client.list_credentials.__doc__)


@click.command(short_help=doc.short_description, help=doc.long_description)
@helpers.user_configurable
def list(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).list_credentials(**other_args)
