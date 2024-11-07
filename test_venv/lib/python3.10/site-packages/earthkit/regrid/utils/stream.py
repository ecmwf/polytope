# (C) Copyright 2023 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation
# nor does it submit to any jurisdiction.
#


from struct import pack, unpack

TAG_ZERO = 0
TAG_START_OBJ = 1
TAG_END_OBJ = 2
TAG_CHAR = 3
TAG_UNSIGNED_CHAR = 4
TAG_INT = 5
TAG_UNSIGNED_INT = 6
TAG_SHORT = 7
TAG_UNSIGNED_SHORT = 8
TAG_LONG = 9
TAG_UNSIGNED_LONG = 10
TAG_LONG_LONG = 11
TAG_UNSIGNED_LONG_LONG = 12
TAG_FLOAT = 13
TAG_DOUBLE = 14
TAG_STRING = 15
TAG_BLOB = 16
TAG_EXCEPTION = 17
TAG_START_REC = 18
TAG_END_REC = 19
TAG_EOF = 20
TAG_LARGE_BLOB = 21  # For blobs >= 2Gb
LAST_TAG = 22

TAG_NAME = (
    "0",
    "start of object",
    "end of object",
    "char",
    "unsigned char",
    "int",
    "unsigned int",
    "short",
    "unsigned short",
    "long",
    "unsigned long",
    "long long",
    "unsigned long long",
    "float",
    "double",
    "string",
    "blob",
    "exception",
    "start of record",
    "end of record",
)


class Stream:
    def __init__(self, stream):
        self.stream = stream

    def _read(self, n):
        return self.stream.read(n)

    def read_tag(self, expected_tag):
        tag = self._read(1)
        tag = ord(tag)

        while tag == TAG_END_OBJ:
            tag = self._read(1)
            if tag:
                tag = ord(tag)

        # TODO There is some suspicious code on the perl side for the following.
        # TODO Maybe worth having a look at it sometime.
        if tag != expected_tag:
            if tag < len(TAG_NAME):
                raise RuntimeError(
                    "Unexpected tag: %s, wanted %s"
                    % (TAG_NAME[tag], TAG_NAME[expected_tag])
                )
            else:
                raise RuntimeError("Invalid tag with id: '%s'" % tag)

        return tag

    def write_tag(self, tag):
        self._write(pack("b", tag), 1)

    def next_object(self):
        while 1:
            tag = self.stream.recv(1)
            if tag == "":
                return 0

            tag = unpack("b", tag)[0]

            if tag == TAG_START_OBJ:
                return 1
            else:
                if tag < len(TAG_NAME):
                    raise RuntimeError(
                        "Unexpected tag: '%s', wanted '%s'"
                        % (TAG_NAME[tag], TAG_NAME[TAG_START_OBJ])
                    )
                else:
                    raise RuntimeError("Invalid tag with id: '%d'" % tag)

    def write_char(self, c):
        self.write_tag(TAG_CHAR)
        self._write(c, 1)

    def write_unsigned_char(self, c):
        self.write_tag(TAG_UNSIGNED_CHAR)
        self._write(c, 1)

    def write_int(self, n):
        self.write_tag(TAG_INT)
        self._write(pack("!L", n), 4)

    def write_unsigned_int(self, n):
        self.write_tag(TAG_UNSIGNED_INT)
        self._write(pack("!L", n), 4)

    def write_long(self, n):
        self.write_tag(TAG_LONG)
        self._write(pack("!L", n), 4)

    def write_double(self, n):
        self.write_tag(TAG_DOUBLE)
        raise RuntimeError("write_doble")

    def write_unsigned_long(self, n):
        self.write_tag(TAG_UNSIGNED_LONG)
        self._write(pack("!L", n), 4)

    def write_long_long(self, n):
        self.write_tag(TAG_LONG_LONG)

        # TODO Error handling when the number is too long.
        # TODO See the perl.

        self._write(pack("!L", n), 4)

    def write_unsigned_long_long(self, n):
        self.write_tag(TAG_UNSIGNED_LONG_LONG)

        # TODO Error handling when input value too big.

        self._write(pack("!L", 0), 4)
        self._write(pack("!L", n), 4)

    def write_string(self, s):
        self.write_tag(TAG_STRING)
        n = len(s)
        self._write(pack("!L", n), 4)
        self._write(s, n)

    def read_char(self):
        self.read_tag(TAG_CHAR)
        return self._read(1)

    def read_unsigned_char(self):
        self.read_tag(TAG_UNSIGNED_CHAR)
        return self._read(1)

    def read_int(self):
        self.read_tag(TAG_INT)
        return unpack("!L", self._read(4))[0]

    def read_unsigned_int(self):
        self.read_tag(TAG_UNSIGNED_INT)
        return unpack("!L", self._read(4))[0]

    def read_long(self):
        self.read_tag(TAG_LONG)
        return unpack("!L", self._read(4))[0]

    def read_double(self):
        self.read_tag(TAG_DOUBLE)
        raise RuntimeError("read_double")

    def read_unsigned_long(self):
        self.read_tag(TAG_UNSIGNED_LONG)
        return unpack("!L", self._read(4))[0]

    def read_long_long(self):
        self.read_tag(TAG_LONG_LONG)
        raise RuntimeError("read_long_long")

    def _read_long_long(self):
        return unpack("!Q", self._read(8))[0]
        # TODO: use 'Q' instead of 'L' for 64-bit ints
        x = unpack("!L", self._read(4))[0]
        y = unpack("!L", self._read(4))[0]

        return (x << 32) | y

    def read_unsigned_long_long(self):
        self.read_tag(TAG_UNSIGNED_LONG_LONG)
        return unpack("!Q", self._read(8))[0]

    def read_string(self):
        self.read_tag(TAG_STRING)
        n = unpack("!L", self._read(4))[0]
        return self._read(n)

    def read_large_blob(self):
        self.read_tag(TAG_LARGE_BLOB)
        len = unpack("!Q", self._read(8))[0]
        return self._read(len)

    def start_object(self):
        self.write_tag(TAG_START_OBJ)

    def end_object(self):
        self.write_tag(TAG_END_OBJ)

    def read_object(self):
        if not self.next_object():
            return None
        klass = self.read_string()
        return klass

    def write_object(self, name, ref):
        self.start_object()

        self.write_string(name)
        self.write_string(ref)

        self.end_object()
