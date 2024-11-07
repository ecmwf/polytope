from enum import IntEnum, unique

from .lib import ffi, lib, ODCException


@unique
class DataType(IntEnum):
    IGNORE = lib.ODC_IGNORE
    INTEGER = lib.ODC_INTEGER
    DOUBLE = lib.ODC_DOUBLE
    REAL = lib.ODC_REAL
    STRING = lib.ODC_STRING
    BITFIELD = lib.ODC_BITFIELD


IGNORE = DataType.IGNORE
INTEGER = DataType.INTEGER
REAL = DataType.REAL
STRING = DataType.STRING
BITFIELD = DataType.BITFIELD
DOUBLE = DataType.DOUBLE


_type_names = {}

def type_name(typ):
    try:
        return _type_names[typ]
    except KeyError:
        try:
            pname = ffi.new("const char**")
            lib.odc_column_type_name(typ, pname)
            name = ffi.string(pname[0]).decode("utf-8")
        except ODCException:
            name = "<unknown>"
        _type_names[typ] = name
        return name
