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
import os

from earthkit.regrid.db import VERSION, MatrixIndex

from .mir import mir_cached_matrix_to_file


def regular_ll(entry):
    bb = entry["bbox"]
    d = {
        "grid": [entry["increments"][x] for x in ("west_east", "south_north")],
        "shape": [entry["nj"], entry["ni"]],
        "area": [bb["north"], bb["west"], bb["south"], bb["east"]],
    }
    if "global" in entry:
        d["global"] = entry["global"]
    return d


def reduced_gg(entry):
    pl = entry["pl"]
    G = "O" if pl[1] - pl[0] == 4 else "N"
    N = entry["N"]
    bb = entry["bbox"]

    d = {
        "grid": f"{G}{N}",
        "shape": [sum(pl)],
        "area": [bb["north"], bb["west"], bb["south"], bb["east"]],
    }

    if "global" in entry:
        d["global"] = entry["global"]

    return d


def healpix(entry):
    d = {"grid": entry["grid"], "ordering": entry["ordering"]}
    return d


def make_sha(d):
    m = hashlib.sha256()
    m.update(json.dumps(d, sort_keys=True).encode("utf-8"))
    return m.hexdigest()


def make_matrix(
    input_path, output_path, index_file=None, global_input=None, global_output=None
):
    with open(input_path) as f:
        entry = json.load(f)

    inter_ori = dict(entry["interpolation"])
    method = entry["interpolation"]["method"]
    uid = MatrixIndex.make_interpolation_uid(entry)
    if uid != method:
        entry["interpolation"]["_uid"] = uid

    # create output folder
    matrix_output_path = os.path.join(
        output_path,
        MatrixIndex.matrix_dir_name(entry),
        # f"{inter_engine}_{inter_version}_{inter_uid}"
    )
    os.makedirs(matrix_output_path, exist_ok=True)

    # create matrix
    cache_file = entry["matrix"].pop("cache_file")
    m = {}
    m["input"] = entry["input"]
    m["output"] = entry["output"]
    m["interpolation"] = inter_ori
    key = make_sha(m)
    name = key

    print(f"entry={entry}")
    npz_file = os.path.join(matrix_output_path, f"{name}.npz")
    mir_cached_matrix_to_file(cache_file, npz_file)

    if index_file is None:
        index_file = os.path.join(output_path, "index.json")

    if os.path.exists(index_file):
        with open(index_file) as f:
            index = json.load(f)
            if index.get("version", None) != VERSION:
                raise ValueError(f"{index_file=} version must be {VERSION}")
    else:
        index = {}
        index["version"] = VERSION
        index["matrix"] = {}

    def convert(x):
        proc = globals()[x["type"]]
        return proc(x)

    if global_input is not None and "global" not in entry["input"]:
        entry["input"]["global"] = 1 if global_input else 0

    if global_output is not None and "global" not in entry["output"]:
        entry["output"]["global"] = 1 if global_output else 0

    index["matrix"][key] = dict(
        input=convert(entry["input"]),
        output=convert(entry["output"]),
        interpolation=entry["interpolation"],
    )

    with open(index_file, "w") as f:
        json.dump(index, f, indent=4)

    print("Written", npz_file)
    print("Written", index_file)
