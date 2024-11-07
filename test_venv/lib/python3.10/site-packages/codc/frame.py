from .constants import BITFIELD, DOUBLE, INTEGER, REAL, STRING, DataType, type_name
from .lib import ffi, lib, memoize_constant

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

import codecs
import os

import numpy as np
import pandas


# A null-terminated UTF-8 decoder
def null_utf_decoder(name):
    if name == "utf_8_null":
        utf8_decoder = codecs.getdecoder("utf-8")

        return codecs.CodecInfo(
            name="utf_8_null",
            encode=None,
            decode=lambda b, e: utf8_decoder(b.split(b"\x00", 1)[0], e),
            incrementalencoder=None,
            incrementaldecoder=None,
            streamwriter=None,
            streamreader=None,
        )


codecs.register(null_utf_decoder)


class ColumnInfo:
    class Bitfield:
        def __init__(self, name, size, offset):
            self.name = name
            self.size = size
            self.offset = offset

        def __eq__(self, other):
            return self.name == other.name and self.size == other.size and self.offset == other.offset

        def __str__(self):
            return f"bits(name={self.name}, size={self.size}, offset={self.offset})"

        def __repr__(self):
            return str(self)

    def __init__(self, name, idx, dtype, datasize, bitfields):
        self.name = name
        self.dtype = dtype
        self.index = idx
        self.datasize = datasize
        self.bitfields = bitfields
        assert (dtype == BITFIELD) != (bitfields is None)
        if self.bitfields:
            assert isinstance(self.bitfields, Iterable)
            assert all(isinstance(b, ColumnInfo.Bitfield) for b in self.bitfields)

    def __str__(self):
        if self.bitfields is not None:
            bitfield_str = "(" + ",".join("{}:{}".format(b.name, b.size) for b in self.bitfields) + ")"
        else:
            bitfield_str = ""
        return "{}:{}{}".format(self.name, type_name(self.dtype), bitfield_str)

    def __repr__(self):
        return str(self)


class Frame:
    def __init__(self, table):
        self.__frame = table
        self.__columns = None

    @property
    @memoize_constant
    def columns(self):
        columns = []
        for col in range(self.ncolumns):
            pname = ffi.new("const char**")
            ptype = ffi.new("int*")
            pdatasize = ffi.new("int*")
            pbitfield_count = ffi.new("int*")
            lib.odc_frame_column_attributes(self.__frame, col, pname, ptype, pdatasize, pbitfield_count)
            name = ffi.string(pname[0]).decode("utf-8")
            dtype = DataType(int(ptype[0]))
            datasize = int(pdatasize[0])
            bitfield_count = int(pbitfield_count[0])
            bitfields = None

            if dtype == STRING:
                assert datasize % 8 == 0
            else:
                assert datasize == 8

            if dtype == BITFIELD:
                bitfields = []
                for n in range(bitfield_count):
                    pbitfield_name = ffi.new("const char**")
                    poffset = ffi.new("int*")
                    psize = ffi.new("int*")
                    lib.odc_frame_bitfield_attributes(self.__frame, col, n, pbitfield_name, poffset, psize)

                    bitfields.append(
                        ColumnInfo.Bitfield(
                            name=ffi.string(pbitfield_name[0]).decode("utf-8"),
                            size=int(psize[0]),
                            offset=int(poffset[0]),
                        )
                    )

            columns.append(ColumnInfo(name, col, dtype, datasize, bitfields))

        return columns

    @property
    @memoize_constant
    def column_dict(self):
        return {c.name: c for c in self.columns}

    @property
    @memoize_constant
    def _simple_column_dict_ambiguous(self):
        columns = {}
        ambiguous_columns = []
        for col in self.columns:
            simple_name = col.name.split("@")[0]
            if simple_name in columns:
                ambiguous_columns.append(simple_name)
            columns[simple_name] = col
        return columns, ambiguous_columns

    @property
    @memoize_constant
    def simple_column_dict(self):
        scd, ambiguous_columns = self._simple_column_dict_ambiguous
        return scd

    @property
    @memoize_constant
    def nrows(self):
        count = ffi.new("long*")
        lib.odc_frame_row_count(self.__frame, count)
        return int(count[0])

    @property
    @memoize_constant
    def ncolumns(self):
        count = ffi.new("int*")
        lib.odc_frame_column_count(self.__frame, count)
        return int(count[0])

    @property
    @memoize_constant
    def properties(self):
        count = ffi.new("int*")
        lib.odc_frame_properties_count(self.__frame, count)

        properties = {}
        for idx in range(int(count[0])):
            key_temp = ffi.new("const char**")
            value_temp = ffi.new("const char**")
            lib.odc_frame_property_idx(self.__frame, idx, key_temp, value_temp)
            key = ffi.string(key_temp[0]).decode("utf-8")
            value = ffi.string(value_temp[0]).decode("utf-8")
            properties[key] = value

        return properties

    def dataframe(self, columns=None):
        # Are there any bitfield columns we need to consider?
        original_columns = columns
        bitfields = []

        if columns is not None:
            final_columns = set()
            _original_columns = self.column_dict.keys()
            _original_simple_columns = self.simple_column_dict.keys()

            for colname in columns:

                # If the column is already present, then use that one directly.
                # This ensures that we can handle exploded bitfield columns, and extract bitfields from
                # existing columns below
                if colname in _original_columns or colname in _original_simple_columns:
                    final_columns.add(colname)
                else:
                    dotpos = colname.find(".")
                    if dotpos == -1:
                        final_columns.add(colname)
                    else:
                        column_name = colname[:dotpos]
                        sp = colname[dotpos + 1 :].split("@")
                        bitfield_name = sp[0]
                        if len(sp) > 1:
                            column_name += "@" + sp[1]
                        final_columns.add(column_name)
                        bitfields.append((bitfield_name, column_name, colname))
            columns = list(final_columns)

        df = self._dataframe_internal(columns)

        # If there are any bitfields that need extraction, do it here, and remove any temporarily
        # decoded columns as is possible

        if bitfields:
            extracted_columns = set()
            for bitfield_name, column_name, output_name in bitfields:
                col = self.column_dict[column_name]
                try:
                    bf = next((b for b in col.bitfields if b.name == bitfield_name))
                except StopIteration:
                    raise KeyError(f"Bitfield '{bitfield_name}' not found")

                # If there are missing values in the column, then it will have been decoded as a float64 to support NaN
                raw_column = df[column_name]
                missing_vals = None
                if raw_column.dtype == np.float64:
                    missing_vals = np.isnan(raw_column)
                    raw_column = raw_column.fillna(value=0).astype("int64")

                mask = (1 << bf.size) - 1
                new_column = np.right_shift(raw_column, bf.offset) & mask
                if bf.size == 1:
                    new_column = new_column.astype(bool)

                # If we have missing values, we need to recreate these
                if missing_vals is not None:
                    new_column[missing_vals] = np.nan

                df[output_name] = new_column
                extracted_columns.add(column_name)

            for column in extracted_columns:
                if column not in original_columns:
                    del df[column]

        return df

    def _dataframe_internal(self, columns=None):
        # Some constants that are useful

        pmissing_integer = ffi.new("long*")
        pmissing_double = ffi.new("double*")
        lib.odc_missing_integer(pmissing_integer)
        lib.odc_missing_double(pmissing_double)
        missing_integer = pmissing_integer[0]
        missing_double = pmissing_double[0]

        # If no column info specified, use the defaults

        if columns is None:
            columns = [c.name for c in self.columns]

        assert columns is not None

        cd = self.column_dict
        scd, ambiguous_columns = self._simple_column_dict_ambiguous

        # Keep track of the column names used, so we can return the correct (fully-qualified, or short)
        # column name for each column
        integer_cols = []
        double_cols = []
        string_cols = {}
        for name in columns:
            try:
                col = cd[name]
            except KeyError:
                if name in ambiguous_columns:
                    raise KeyError("Ambiguous short column name '{}' requested".format(name))
                col = scd[name]
            if col.dtype == INTEGER or col.dtype == BITFIELD:
                integer_cols.append((name, col))
            elif col.dtype == REAL or col.dtype == DOUBLE:
                double_cols.append((name, col))
            elif col.dtype == STRING:
                string_cols.setdefault(col.datasize, []).append((name, col))

        decoder = ffi.new("odc_decoder_t**")
        lib.odc_new_decoder(decoder)
        decoder = ffi.gc(decoder[0], lib.odc_free_decoder)

        lib.odc_decoder_set_row_count(decoder, self.nrows)

        dataframes = []
        pos = 0
        string_seq = tuple((cols, "|S{}".format(dataSize), dataSize) for dataSize, cols in string_cols.items())
        for cols, dtype, dsize in (
            (integer_cols, np.int64, 8),
            (double_cols, np.double, 8),
        ) + string_seq:
            if len(cols) > 0:
                array = np.empty((self.nrows, len(cols)), dtype=dtype, order="C")

                pointer = array.ctypes.data
                strides = array.ctypes.strides

                colnames = []
                for i, (name, col) in enumerate(cols):
                    colnames.append(name)
                    lib.odc_decoder_add_column(decoder, col.name.encode("utf-8"))
                    lib.odc_decoder_column_set_data_array(
                        decoder,
                        pos,
                        dsize,
                        strides[0],
                        ffi.cast("void*", pointer + (i * strides[1])),
                    )
                    pos += 1

                dataframes.append(pandas.DataFrame(array, columns=colnames, copy=False))

        try:
            threads = len(os.shed_getaffinity(0))
        except AttributeError:
            threads = os.cpu_count()

        prows_decoded = ffi.new("long*")
        lib.odc_decode_threaded(decoder, self.__frame, prows_decoded, threads)
        assert prows_decoded[0] == self.nrows

        # Update the missing values (n.b., still sorted by type), and decode strings

        for i in range(len(dataframes)):
            df = dataframes[i]
            if df.dtypes[0] == np.int64:
                df.mask(df == missing_integer, inplace=True)
            elif df.dtypes[0] == np.double:
                df.mask(df == missing_double, inplace=True)
            else:
                # This is a bit yucky, but I haven't found any other way to decode from b'' strings to real ones
                # Also note, result_type added to work around bug in pandas
                # https://github.com/pandas-dev/pandas/issues/34529
                dataframes[i] = df.apply(
                    lambda x: x.astype("object").str.decode("utf_8_null"),
                    result_type="expand",
                )

        # And construct the DataFrame from the decoded data

        if len(dataframes) == 1:
            return dataframes[0]
        else:
            return pandas.concat(dataframes, copy=False, axis=1)
