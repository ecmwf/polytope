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

# set
doc = parse(Client.set_config.__doc__)


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
        + doc.long_description
    ),
)
@click.argument("key", type=str)
@click.argument("value", type=str)
@helpers.user_configurable
def set(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).set_config(persist=True, **other_args)


# unset
doc = parse(Client.unset_config.__doc__)


@click.command(
    short_help=doc.short_description,
    help=(doc.params[0].arg_name.upper() + ": " + doc.params[0].description + "\n\n" + doc.long_description),
)
@click.argument("key", type=str)
@helpers.user_configurable
def unset(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).unset_config(persist=True, **other_args)


# list
doc = parse(Client.list_config.__doc__)


@click.command(short_help=doc.short_description, help=doc.long_description)
@helpers.user_configurable
def list(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).list_config(**other_args)
