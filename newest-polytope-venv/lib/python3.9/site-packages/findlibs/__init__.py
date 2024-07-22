#!/usr/bin/env python3
# (C) Copyright 2020 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#

import ctypes.util
import os
import sys

__version__ = "0.0.5"

EXTENSIONS = {
    "darwin": ".dylib",
    "win32": ".dll",
}


def find(lib_name, pkg_name=None):
    """Returns the path to the selected library, or None if not found.

    Args:
        lib_name (str): Library name without the `lib` prefix
        pkg_name (str, optional): Package name if it differs from the library name.
            Defaults to None.

    Returns:
        str | None: Path to selected library
    """

    pkg_name = pkg_name or lib_name
    extension = EXTENSIONS.get(sys.platform, ".so")

    # sys.prefix/lib, $CONDA_PREFIX/lib has highest priority;
    # otherwise, system library may mess up anaconda's virtual environment.

    roots = [sys.prefix]
    if "CONDA_PREFIX" in os.environ:
        roots.append(os.environ["CONDA_PREFIX"])

    for root in roots:
        for lib in ("lib", "lib64"):
            fullname = os.path.join(root, lib, "lib{}{}".format(lib_name, extension))
            if os.path.exists(fullname):
                return fullname

    env_prefixes = [pkg_name.upper(), pkg_name.lower()]
    env_suffixes = ["HOME", "DIR"]
    envs = ["{}_{}".format(x, y) for x in env_prefixes for y in env_suffixes]

    for env in envs:
        if env in os.environ:
            home = os.path.expanduser(os.environ[env])
            for lib in ("lib", "lib64"):
                fullname = os.path.join(
                    home, lib, "lib{}{}".format(lib_name, extension)
                )
                if os.path.exists(fullname):
                    return fullname

    for path in (
        "LD_LIBRARY_PATH",
        "DYLD_LIBRARY_PATH",
    ):
        for home in os.environ.get(path, "").split(":"):
            fullname = os.path.join(home, "lib{}{}".format(lib_name, extension))
            if os.path.exists(fullname):
                return fullname

    for root in ("/", "/usr/", "/usr/local/", "/opt/", "/opt/homebrew/"):
        for lib in ("lib", "lib64"):
            fullname = os.path.join(root, lib, "lib{}{}".format(lib_name, extension))
            if os.path.exists(fullname):
                return fullname

    return ctypes.util.find_library(lib_name)
