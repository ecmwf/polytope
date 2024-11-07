import struct

import pandas as pd

from .constants import INTERNAL_REAL_MISSING, MISSING_INTEGER, MISSING_REAL, MISSING_STRING, DataType


class Codec:
    def __init__(
        self,
        column_name: str,
        minval: float,
        maxval: float,
        data_type: DataType,
        has_missing: bool = False,
        bitfield_names=None,
        bitfield_sizes=None,
    ):
        self.column_name = column_name
        self.min = minval
        self.max = maxval
        self.has_missing = has_missing
        self.bitfield_names = bitfield_names
        self.bitfield_sizes = bitfield_sizes

        self.type = data_type
        self.missing_value = {
            DataType.INTEGER: MISSING_INTEGER,
            DataType.BITFIELD: MISSING_INTEGER,
            DataType.DOUBLE: MISSING_REAL,
            DataType.REAL: MISSING_REAL,
            DataType.STRING: MISSING_STRING,
        }[data_type]
        self.typed_missing_value = {
            DataType.INTEGER: None,
            DataType.BITFIELD: None,
            DataType.DOUBLE: None,
            DataType.REAL: None,
            DataType.STRING: "",
        }[data_type]

        assert self.name is not None

    @property
    def name(self):
        return "".join("_" + c.lower() if c.isupper() else c for c in self.__class__.__name__).strip("_")

    @staticmethod
    def codec_class_name(name):
        return "".join(part[:1].upper() + part[1:] for part in name.split("_"))

    @property
    def data_size(self):
        """
        Size of the decoded data in bytes.
        """
        return 8

    def encode_header(self, stream):
        stream.encodeString(str(self.column_name))
        stream.encodeInt32(self.type)

        if self.type == DataType.BITFIELD:
            assert len(self.bitfield_sizes) == len(self.bitfield_names)
            stream.encodeInt32(len(self.bitfield_names))
            for nm in self.bitfield_names:
                stream.encodeString(nm)
            stream.encodeInt32(len(self.bitfield_sizes))
            for sz in self.bitfield_sizes:
                stream.encodeInt32(sz)

        stream.encodeString(self.name)
        stream.encodeInt32(1 if self.has_missing else 0)
        stream.encodeReal64(self.min)
        stream.encodeReal64(self.max)
        stream.encodeReal64(self.missing_value)

    @staticmethod
    def read_core_header(stream):
        has_missing = False if stream.readInt32() == 0 else True
        minval = stream.readReal64()
        maxval = stream.readReal64()
        missing_value = stream.readReal64()
        return has_missing, minval, maxval, missing_value

    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields):
        raise NotImplementedError

    @classmethod
    def from_stream(cls, stream, column_name: str, data_type: DataType, bitfield_names, bitfield_sizes):
        has_missing, minval, maxval, missing_value = cls.read_core_header(stream)
        return cls(
            column_name,
            minval,
            maxval,
            data_type,
            has_missing=has_missing,
            bitfield_names=bitfield_names,
            bitfield_sizes=bitfield_sizes,
        )

    def encode(self, stream, value):
        raise NotImplementedError

    def decode(self, stream):
        raise NotImplementedError

    @property
    def numChanges(self):
        raise NotImplementedError


# n.b. The codec names match the class names


class Constant(Codec):
    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields: list):
        assert data.nunique() == 1 and not data.hasnans
        value = next(iter(data))

        if bitfields:
            assert data_type == DataType.BITFIELD
            bitfield_names = [bf if isinstance(bf, str) else bf[0] for bf in bitfields]
            bitfield_sizes = [1 if isinstance(bf, str) else bf[1] for bf in bitfields]
        else:
            bitfield_names = []
            bitfield_sizes = []

        return cls(
            column_name,
            minval=value,
            maxval=value,
            data_type=data_type,
            has_missing=False,
            bitfield_names=bitfield_names,
            bitfield_sizes=bitfield_sizes,
        )

    def encode(self, stream, value):
        pass

    def decode(self, stream):
        return {DataType.INTEGER: int, DataType.REAL: float, DataType.DOUBLE: float, DataType.BITFIELD: int}[self.type](
            self.min
        )

    @property
    def numChanges(self):
        return 0


class ConstantString(Constant):
    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields):
        assert data.nunique() == 1 and not data.hasnans
        assert data_type == DataType.STRING
        assert not bitfields

        # n.b. This looks like it ties it to little-endian, but it doesn't. Byte order
        #      is always the same for string data, but we are 'pretending' to be a double.
        value = struct.unpack("<d", (next(iter(data)).encode("utf-8") + (b"\x00" * 8))[:8])[0]

        return cls(column_name, value, value, data_type)

    def decode(self, stream):
        return struct.pack("<d", self.min).split(b"\x00", 1)[0].decode("utf-8")


class NumericBase(Codec):
    _numChanges = None
    _data = None
    accepted_types = None

    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields):
        assert data_type in cls.accepted_types
        if bitfields:
            assert data_type == DataType.BITFIELD
            bitfield_names = [bf if isinstance(bf, str) else bf[0] for bf in bitfields]
            bitfield_sizes = [1 if isinstance(bf, str) else bf[1] for bf in bitfields]
        else:
            bitfield_names = []
            bitfield_sizes = []
        c = cls(
            column_name,
            data.min(),
            data.max(),
            data_type,
            has_missing=data.hasnans,
            bitfield_names=bitfield_names,
            bitfield_sizes=bitfield_sizes,
        )
        c._data = data
        return c

    @property
    def numChanges(self):
        if self._numChanges is None:
            assert self._data is not None
            self._numChanges = (self._data.fillna(self.missing_value).diff() != 0).sum() - 1
        return self._numChanges


class ConstantOrMissing(NumericBase):
    internal_missing_value = 0xFF
    accepted_types = (DataType.INTEGER, DataType.BITFIELD)

    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields):
        assert data.nunique() == 1 and data.hasnans
        return super().from_dataframe(column_name, data, data_type, bitfields)

    def encode(self, stream, value):
        if pd.isnull(value):
            stream.encodeUInt8(self.internal_missing_value)
        else:
            stream.encodeUInt8(0)

    def decode(self, stream):
        marker = stream.readUInt8()
        if marker == self.internal_missing_value:
            return None
        else:
            return {DataType.INTEGER: int, DataType.REAL: float, DataType.DOUBLE: float, DataType.BITFIELD: int}[
                self.type
            ](self.min)


class RealConstantOrMissing(ConstantOrMissing):
    accepted_types = (DataType.DOUBLE, DataType.REAL)


class OffsetInteger(NumericBase):
    internal_missing_value = None
    max_range = 0
    accepted_types = (DataType.INTEGER, DataType.BITFIELD)

    @staticmethod
    def _encode(stream, value):
        raise NotImplementedError

    @staticmethod
    def _decode(stream):
        raise NotImplementedError

    def encode(self, stream, value):
        if pd.isnull(value):
            self._encode(stream, self.internal_missing_value)
        else:
            assert float(value).is_integer()
            assert value - self.min <= self.max_range
            self._encode(stream, int(value - self.min))

    def decode(self, stream):
        value = self._decode(stream)
        return None if value == self.internal_missing_value else int(value + self.min)


class Int8(OffsetInteger):
    max_range = 0xFF
    accepts_missing = False

    @staticmethod
    def _encode(stream, value):
        stream.encodeUInt8(value)

    @staticmethod
    def _decode(stream):
        return stream.readUInt8()


class Int8Missing(Int8):
    max_range = 0xFE
    accepts_missing = True
    internal_missing_value = 0xFF


class Int16(OffsetInteger):
    max_range = 0xFFFF
    accepts_missing = False

    @staticmethod
    def _encode(stream, value):
        stream.encodeUInt16(value)

    @staticmethod
    def _decode(stream):
        return stream.readUInt16()


class Int16Missing(Int16):
    max_range = 0xFFFE
    accepts_missing = True
    internal_missing_value = 0xFFFF


class Int32(NumericBase):
    max_range = 0xFFFFFFFE
    accepts_missing = True
    internal_missing_value = 0x7FFFFFFF
    accepted_types = (DataType.INTEGER, DataType.BITFIELD)

    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields):
        if data.min() < -0x80000000 or data.max() >= 0x7FFFFFFF:
            raise ValueError("Cannot encode integers out of range")
        c = super().from_dataframe(column_name, data, data_type, bitfields)
        assert c.missing_value == c.internal_missing_value
        return c

    def encode(self, stream, value):
        if pd.isnull(value):
            stream.encodeInt32(self.internal_missing_value)
        else:
            stream.encodeInt32(int(value))

    def decode(self, stream):
        value = stream.readInt32()
        return None if value == self.internal_missing_value else value


class LongReal(NumericBase):
    accepted_types = (DataType.DOUBLE, DataType.REAL)

    def encode(self, stream, value):
        stream.encodeReal64(value)

    def decode(self, stream):
        return stream.readReal64()


class ShortReal(NumericBase):
    internal_missing_value = INTERNAL_REAL_MISSING[0]
    accepted_types = (DataType.DOUBLE, DataType.REAL)

    def encode(self, stream, value):
        if pd.isnull(value) is None:
            stream.encodeReal32(self.internal_missing_value)
        else:
            assert value != self.internal_missing_value
            stream.encodeReal32(value)

    def decode(self, stream):
        value = stream.readReal32()
        return None if value == self.internal_missing_value else value


class ShortReal2(ShortReal):
    internal_missing_value = INTERNAL_REAL_MISSING[1]


class Int8String(Codec):
    missing_value = MISSING_INTEGER
    type = DataType.STRING
    _numChanges = None

    def __init__(self, *args, values=None, data=None, **kwargs):
        self._data = data
        assert values is not None
        self.values = values
        self.value_map = {value: i for i, value in enumerate(values)}

        super().__init__(*args, **kwargs)

    @classmethod
    def from_dataframe(cls, column_name: str, data: pd.Series, data_type: DataType, bitfields):
        assert not data.hasnans
        assert data_type == DataType.STRING
        assert not bitfields
        return cls(column_name, 0, 0, data_type, values=data.unique(), data=data)

    @classmethod
    def from_stream(cls, stream, column_name: str, data_type: DataType, bitfield_names, bitfield_sizes):
        has_missing, minval, maxval, missing_value = cls.read_core_header(stream)
        nvalues = stream.readInt32()
        values = [None] * nvalues
        for _ in range(nvalues):
            value = stream.readString()
            stream.readInt32()  # discard
            idx = stream.readInt32()
            values[idx] = value
        assert not any(v is None for v in values)
        return cls(
            column_name,
            minval,
            maxval,
            data_type,
            values=values,
            has_missing=has_missing,
            bitfield_names=bitfield_names,
            bitfield_sizes=bitfield_sizes,
        )

    @staticmethod
    def _encode(stream, value):
        stream.encodeUInt8(value)

    @staticmethod
    def _decode(stream):
        return stream.readUInt8()

    def encode_header(self, stream):
        super().encode_header(stream)
        stream.encodeInt32(len(self.value_map))
        for value, idx in self.value_map.items():
            stream.encodeString(value)
            stream.encodeInt32(0)
            stream.encodeInt32(idx)

    def encode(self, stream, value):
        idx = self.value_map[value]
        self._encode(stream, idx)

    def decode(self, stream):
        idx = self._decode(stream)
        return self.values[idx]

    @property
    def numChanges(self):
        if self._numChanges is None:
            assert self._data is not None
            self._numChanges = (self._data != self._data.shift()).sum() - 1
        return self._numChanges


class Int16String(Int8String):
    @staticmethod
    def _encode(stream, value):
        stream.encodeUInt16(value)

    @staticmethod
    def _decode(stream):
        return stream.readUInt16()


def select_codec(column_name: str, data: pd.Series, data_type, bitfields):
    # If data types are not specified, determine them from the pandas Series

    if data_type is None:
        if data.dtype in ["{}int{}".format(s, b) for s in ("", "u") for b in (8, 16, 32, 64)]:
            data_type = DataType.INTEGER
        elif data.dtype == "float64":
            if not data.isnull().all() and all(pd.isnull(v) or float(v).is_integer() for v in data):
                data_type = DataType.INTEGER
            else:
                data_type = DataType.DOUBLE
        elif data.dtype == "float32":
            data_type = DataType.REAL
        elif data.dtype == "object" or pd.api.types.is_string_dtype(data):
            if not data.isnull().all() and all(s is None or isinstance(s, str) for s in data):
                data_type = DataType.STRING

    if data_type is None:
        raise RuntimeError("Unknown data type {} not supported".format(data.dtype))

    # And now the logic for selecting the codec

    codec_class = None

    if data_type in (DataType.INTEGER, DataType.BITFIELD):
        range = data.max() - data.min()
        has_missing = data.hasnans

        if data.nunique() == 1:
            if data.hasnans:
                codec_class = ConstantOrMissing
            else:
                codec_class = Constant
        else:
            for c in [Int8, Int8Missing, Int16, Int16Missing, Int32]:
                if range <= c.max_range and (c.accepts_missing or not has_missing):
                    codec_class = c
                    break

    elif data_type == DataType.DOUBLE:
        if data.nunique() == 1:
            if data.hasnans:
                codec_class = RealConstantOrMissing
            else:
                codec_class = Constant
        else:
            codec_class = LongReal

    elif data_type == DataType.REAL:
        if data.nunique() == 1:
            if data.hasnans:
                codec_class = RealConstantOrMissing
            else:
                codec_class = Constant
        elif INTERNAL_REAL_MISSING[1] in data:
            if INTERNAL_REAL_MISSING[0] in data:
                raise ValueError("Cannot encode a float data series with both internal missing values")
            codec_class = ShortReal
        else:
            codec_class = ShortReal2

    elif data_type == DataType.STRING:
        if data.nunique() == 1 and len(data.iloc[0]) <= 8 and not data.hasnans:
            codec_class = ConstantString
        elif data.nunique() <= 256:
            codec_class = Int8String
        else:
            assert data.nunique() <= 32767
            codec_class = Int16String

    if codec_class is not None:
        return codec_class.from_dataframe(column_name, data, data_type, bitfields)

    print(data)
    print(data_type)
    raise NotImplementedError


def read_codec(stream):
    column_name = stream.readString()
    data_type = DataType(stream.readInt32())

    if data_type == DataType.BITFIELD:
        bitFieldNames = [stream.readString() for _ in range(stream.readInt32())]
        bitFieldSizes = [stream.readInt32() for _ in range(stream.readInt32())]
    else:
        bitFieldNames = []
        bitFieldSizes = []

    codec_class = stream.readString()
    codec_class = globals()[Codec.codec_class_name(codec_class)]
    return codec_class.from_stream(stream, column_name, data_type, bitFieldNames, bitFieldSizes)
