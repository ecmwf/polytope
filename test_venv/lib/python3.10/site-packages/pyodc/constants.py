import struct
from enum import IntEnum, unique

# Current version information

FORMAT_VERSION_NUMBER_MAJOR = 0
FORMAT_VERSION_NUMBER_MINOR = 5

# Default missing values

MISSING_INTEGER = 2147483647
MISSING_REAL = -2147483647
MISSING_STRING = struct.unpack("<d", b"\x00\x00\x00\x00\x00\x00\x00\x00")[0]
DECODED_MISSING_STRING = ""

INTERNAL_REAL_MISSING = (
    struct.unpack("<f", b"\x00\x00\x80\x00")[0],
    struct.unpack("<f", b"\xff\xff\x7f\x7f")[0],
)

# Constants for header encoding

NEW_HEADER = 65535
MAGIC = b"ODA"
ENDIAN_MARKER = 1

# Types


@unique
class DataType(IntEnum):
    """
    Defines the encoded data type for a specified column
    """

    IGNORE = 0  #: Ignore value
    INTEGER = 1  #: Integer value
    REAL = 2  #: Real value
    STRING = 3  #: String value
    BITFIELD = 4  #: Bitfield value
    DOUBLE = 5  #: Double value


IGNORE = DataType.IGNORE
INTEGER = DataType.INTEGER
REAL = DataType.REAL
STRING = DataType.STRING
BITFIELD = DataType.BITFIELD
DOUBLE = DataType.DOUBLE

TYPE_NAMES = {
    IGNORE: "ignore",
    INTEGER: "integer",
    REAL: "real",
    STRING: "string",
    BITFIELD: "bitfield",
    DOUBLE: "double",
}
