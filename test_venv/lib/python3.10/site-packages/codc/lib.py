#
# Copyright 2017-2020 European Centre for Medium-Range Weather Forecasts (ECMWF).
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os

import cffi
import findlibs
from pkg_resources import parse_version

__odc_version__ = "1.4.0"

ffi = cffi.FFI()


class ODCException(RuntimeError):
    pass


class CFFIModuleLoadFailed(ODCException):
    pass


class PatchedLib:
    """
    Patch a CFFI library with error handling

    Finds the header file associated with the ODC C API and parses it, loads the shared library,
    and patches the accessors with automatic python-C error handling.
    """

    __type_names = {}

    def __init__(self):
        ffi.cdef(self.__read_header())

        library_path = findlibs.find("odccore", pkg_name="odc")
        if library_path is None:
            raise RuntimeError("Cannot find the odccore library")

        self.__lib = ffi.dlopen(library_path)

        # Todo: Version check against __version__

        # All of the executable members of the CFFI-loaded library are functions in the ODC
        # C API. These should be wrapped with the correct error handling. Otherwise forward
        # these on directly.

        for f in dir(self.__lib):
            try:
                attr = getattr(self.__lib, f)
                setattr(self, f, self.__check_error(attr, f) if callable(attr) else attr)
            except Exception as e:
                print(e)
                print("Error retrieving attribute", f, "from library")

        # Initialise the library, and sett it up for python-appropriate behaviour

        self.odc_initialise_api()
        self.odc_integer_behaviour(self.ODC_INTEGERS_AS_LONGS)

        # Check the library version

        tmp_str = ffi.new("char**")
        self.odc_version(tmp_str)
        versionstr = ffi.string(tmp_str[0]).decode("utf-8")

        if parse_version(versionstr) < parse_version(__odc_version__):
            raise RuntimeError("Version of libodc found is too old. {} < {}".format(versionstr, __odc_version__))

    def type_name(self, dtype: "DataType"):  # noqa: F821
        name = self.__type_names.get(dtype, None)
        if name is not None:
            return name

        name_tmp = ffi.new("char**")
        self.odc_column_type_name(dtype, name_tmp)
        name = ffi.string(name_tmp[0]).decode("utf-8")
        self.__type_names[dtype] = name
        return name

    def __read_header(self):
        with open(os.path.join(os.path.dirname(__file__), "processed_odc.h"), "r") as f:
            return f.read()

    def __check_error(self, fn, name):
        """
        If calls into the ODC library return errors, ensure that they get detected and reported
        by throwing an appropriate python exception.
        """

        def wrapped_fn(*args, **kwargs):
            retval = fn(*args, **kwargs)
            if retval not in (
                self.__lib.ODC_SUCCESS,
                self.__lib.ODC_ITERATION_COMPLETE,
            ):
                error_str = "Error in function {}: {}".format(name, self.__lib.odc_error_string(retval))
                raise ODCException(error_str)
            return retval

        return wrapped_fn


def memoize_constant(fn):
    """Memoize constant values to avoid repeatedly crossing the API layer unecessarily"""
    attr_name = "__memoized_{}".format(fn.__name__)

    def wrapped_fn(self):
        value = getattr(self, attr_name, None)
        if value is None:
            value = fn(self)
            setattr(self, attr_name, value)
        return value

    return wrapped_fn


# Bootstrap the library

try:
    lib = PatchedLib()
except CFFIModuleLoadFailed as e:
    raise ImportError() from e
