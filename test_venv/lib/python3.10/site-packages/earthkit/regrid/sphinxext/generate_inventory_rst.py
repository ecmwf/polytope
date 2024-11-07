# (C) Copyright 2023 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import hashlib
import json
from collections import defaultdict, namedtuple

from earthkit.regrid.db import SYS_DB as DB
from earthkit.regrid.gridspec import GridSpec

Specs = namedtuple("Specs", ["source", "target"])


BLOCK_COL_NUM = 3


def to_str(gs):
    if isinstance(gs, str):
        return gs
    return {"grid": gs["grid"]}


def make_gs_block(source, target):
    while len(target) % BLOCK_COL_NUM != 0:
        target.append("")

    step = len(target) // BLOCK_COL_NUM

    source_grid = source["grid"]

    CODE_LINE = "         {}"
    FIRST_COL = """
    * - .. code-block:: python

"""

    OTHER_COL = """
      - .. code-block:: python

"""

    txt = rf"""

{source_grid}
+++++++++++++++++++++++++

Source :ref:`gridspec <gridspec>`:

.. code-block:: python

    {to_str(source)}


Target :ref:`gridspec <gridspec>`\s available for source:

.. list-table::
    :header-rows: 0

"""

    for k in range(BLOCK_COL_NUM):
        txt += FIRST_COL if k == 0 else OTHER_COL
        for i in range(k * step, (k + 1) * step):
            txt += CODE_LINE.format(to_str(target[i])) + "\n"

    return txt


def match(gs, grid):
    for name, val in grid.items():
        if name == "type":
            continue
        if hasattr(gs, name):
            if getattr(gs, name) != val:
                return False
        else:
            return False
    return True


def build_gs_page(specs, grid, long_name):
    txt = f"""

.. include:: pre_gen_warn.rst

This page contains all the available target gridspecs for a given
**{long_name}** source :ref:`gridspec <gridspec>`.

"""

    # print(f"{grid=}\n")
    for _, v in specs.items():
        source = v.source
        target = v.target

        if source["type"] != grid["type"]:
            continue

        if match(source, grid):
            # print(f"->{source=}\n")
            # for t in target:
            # print(f"    {t=}\n")
            txt += make_gs_block(source, target)

    return txt


def load_matrix_index_file():
    specs = defaultdict(Specs)

    for _, entry in DB.index.items():
        gs_in = GridSpec.from_dict(entry["input"])
        gs_out = GridSpec.from_dict(entry["output"])

        if entry["interpolation"]["method"] == "linear":
            # key = dict(grid=gs_in["grid"])
            key = dict(gs_in)
            m = hashlib.sha256()
            m.update(json.dumps(key).encode("utf-8"))
            gs_id = m.hexdigest()

            if gs_id not in specs:
                specs[gs_id] = Specs(gs_in, [gs_out])
            else:
                specs[gs_id].target.append(gs_out)

    return specs


def execute(*args):
    specs = load_matrix_index_file()

    grid_type = args[0]

    gs = {}
    if grid_type == "reduced_gg_o":
        gs["type"] = "reduced_gg"
        gs["octahedral"] = True
    elif grid_type == "reduced_gg":
        gs["type"] = "reduced_gg"
        gs["octahedral"] = False
    elif grid_type == "healpix_ring":
        gs["type"] = "healpix"
        gs["ordering"] = "ring"
    elif grid_type == "healpix_nested":
        gs["type"] = "healpix"
        gs["ordering"] = "nested"
    else:
        gs["type"] = grid_type

    if len(args) >= 2:
        long_name = " ".join(args[1:])
        long_name = long_name.replace('"', "")
    else:
        long_name = grid_type

    # print(f"{gs=}\n")
    txt = build_gs_page(specs, gs, long_name)
    print(txt)


if __name__ == "__main__":
    execute()
