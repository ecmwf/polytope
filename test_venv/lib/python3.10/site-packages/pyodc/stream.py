"""
At this point, we don't worry about being able to encode with cross-endianness.

That may be useful at some point
"""
import struct
from io import SEEK_SET


class Stream:
    byteOrder = None
    floatMarker = None
    doubleMarker = None

    def __init__(self, f):
        self.f = f
        assert self.byteOrder in ["big", "little"]
        assert self.floatMarker in [">f", "<f"]
        assert self.doubleMarker in [">d", "<d"]

    def seek(self, nbytes):
        self.f.seek(nbytes, SEEK_SET)

    def position(self):
        return self.f.tell()

    # Write functionality

    def write(self, b: bytes):
        self.f.write(b)

    def encodeMarker(self, marker: int):
        self.write(marker.to_bytes(2, byteorder="big", signed=False))

    def encodeUInt8(self, value: int):
        self.write(value.to_bytes(1, byteorder=self.byteOrder, signed=False))

    def encodeUInt16(self, value: int):
        self.write(value.to_bytes(2, byteorder=self.byteOrder, signed=False))

    def encodeInt32(self, value: int):
        self.write(value.to_bytes(4, byteorder=self.byteOrder, signed=True))

    def encodeInt64(self, value: int):
        self.write(value.to_bytes(8, byteorder=self.byteOrder, signed=True))

    def encodeString(self, value: str):
        self.encodeByteString(value.encode("utf-8"))

    def encodeByteString(self, value: bytes):
        self.encodeInt32(len(value))
        self.write(value)

    def encodeReal32(self, value: float):
        self.write(struct.pack(self.floatMarker, value))

    def encodeReal64(self, value: float):
        self.write(struct.pack(self.doubleMarker, value))

    # Read functionality

    def read(self, n: int):
        return self.f.read(n)

    def readMarker(self):
        return int.from_bytes(self.read(2), byteorder="big", signed=False)

    def readUInt8(self):
        return int.from_bytes(self.read(1), byteorder=self.byteOrder, signed=False)

    def readUInt16(self):
        return int.from_bytes(self.read(2), byteorder=self.byteOrder, signed=False)

    def readInt32(self):
        return int.from_bytes(self.read(4), byteorder=self.byteOrder, signed=True)

    def readInt64(self):
        return int.from_bytes(self.read(8), byteorder=self.byteOrder, signed=True)

    def readString(self):
        return self.readByteString().decode("utf-8")

    def readByteString(self):
        return self.read(self.readInt32())

    def readReal32(self):
        return struct.unpack(self.floatMarker, self.read(4))[0]

    def readReal64(self):
        return struct.unpack(self.doubleMarker, self.read(8))[0]


class LittleEndianStream(Stream):
    byteOrder = "little"
    floatMarker = "<f"
    doubleMarker = "<d"


class BigEndianStream(Stream):
    byteOrder = "big"
    floatMarker = ">f"
    doubleMarker = ">d"
