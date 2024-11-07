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

# retrieve
doc = parse(Client.retrieve.__doc__)


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
@click.argument("name", type=str)
@click.argument("request", type=str)
@click.argument("output_file", type=str, required=False)
@click.option("inline_request", "-e", "--inline-request", default=False, is_flag=True, help=doc.params[3].description)
@click.option("asynchronous", "-A", "--async", default=False, is_flag=True, help=doc.params[4].description)
@click.option("max_attempts", "-m", "--max-attempts", type=int, help=doc.params[5].description)
@click.option(
    "attempt_period", "-P", "--attempt-period", default=0.1, show_default=True, help=doc.params[6].description
)
@click.option("append", "--append", default=False, is_flag=True, help=doc.params[7].description)
@click.option("pointer", "--pointer", default=False, is_flag=True, help=doc.params[8].description)
@helpers.user_configurable
def retrieve(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).retrieve(**other_args)


# archive
doc = parse(Client.archive.__doc__)


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
@click.argument("name", type=str)
@click.argument("metadata", type=str)
@click.argument("input_url", type=str)
@click.option("inline_metadata", "-e", "--inline-metadata", default=False, is_flag=True, help=doc.params[3].description)
@click.option("asynchronous", "-A", "--async", default=False, is_flag=True, help=doc.params[4].description)
@click.option("max_attempts", "-m", "--max-attempts", type=int, help=doc.params[5].description)
@click.option(
    "attempt_period", "-P", "--attempt-period", default=0.1, show_default=True, help=doc.params[6].description
)
@helpers.user_configurable
def archive(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).archive(**other_args)


# list
doc = parse(Client.list_requests.__doc__)


@click.command(short_help=doc.short_description, help=doc.long_description)
@click.option("collection_id", "--collection", type=str, help=doc.params[0].description)
@helpers.user_configurable
def list(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).list_requests(**other_args)


# describe
doc = parse(Client.describe_request.__doc__)


@click.command(
    short_help=doc.short_description,
    help=(doc.params[0].arg_name.upper() + ": " + doc.params[0].description + "\n\n" + doc.long_description),
)
@click.argument("request_id", type=str)
@helpers.user_configurable
def describe(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).describe_request(**other_args)


# revoke
doc = parse(Client.revoke.__doc__)


@click.command(
    short_help=doc.short_description,
    help=(doc.params[0].arg_name.upper() + ": " + doc.params[0].description + "\n\n" + doc.long_description),
)
@click.argument("request_id", type=str)
@helpers.user_configurable
def revoke(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).revoke(**other_args)


# download
doc = parse(Client.download.__doc__)


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
@click.argument("request_id", type=str)
@click.argument("output_file", type=str, required=False)
@click.option("asynchronous", "-A", "--async", default=False, is_flag=True, help=doc.params[2].description)
@click.option("max_attempts", "-m", "--max-attempts", type=int, help=doc.params[3].description)
@click.option(
    "attempt_period", "-P", "--attempt-period", default=0.1, show_default=True, help=doc.params[4].description
)
@click.option("append", "--append", default=False, is_flag=True, help=doc.params[5].description)
@click.option("pointer", "--pointer", default=False, is_flag=True, help=doc.params[6].description)
@helpers.user_configurable
def download(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).download(**other_args)


# upload
doc = parse(Client.upload.__doc__)


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
@click.argument("request_id", type=str)
@click.argument("input_file", type=str)
@click.option("asynchronous", "-A", "--async", default=False, is_flag=True, help=doc.params[2].description)
@click.option("max_attempts", "-m", "--max-attempts", type=int, help=doc.params[3].description)
@click.option(
    "attempt_period", "-P", "--attempt-period", default=0.1, show_default=True, help=doc.params[4].description
)
@helpers.user_configurable
def upload(**kwargs):
    session_args, other_args = helpers.filter_session_args(**kwargs)
    Client(**session_args).upload(**other_args)
