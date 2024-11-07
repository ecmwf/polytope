#
# (C) Copyright 2014 ECMWF.
#
# This software is licensed under the terms of the Apache Licence Version 2.0
# which can be obtained at http://www.apache.org/licenses/LICENSE-2.0.
# In applying this licence, ECMWF does not waive the privileges and immunities
# granted to it by virtue of its status as an intergovernmental organisation nor
# does it submit to any jurisdiction.
#

from __future__ import absolute_import

from .codec import read_codec
from .constants import (
    BITFIELD,
    ENDIAN_MARKER,
    FORMAT_VERSION_NUMBER_MAJOR,
    FORMAT_VERSION_NUMBER_MINOR,
    MAGIC,
    NEW_HEADER,
    TYPE_NAMES,
)
from .stream import BigEndianStream, LittleEndianStream

try:
    from collections.abc import Iterable
except ImportError:
    from collections import Iterable

from itertools import accumulate, chain

import numpy as np
import pandas as pd


class MismatchedFramesError(ValueError):
    pass


class ColumnInfo:
    """
    Represent the type of a column in the encoded file

    Parameters:
        name(str): The name of the column
        idx(int): The index of the column
        dtype(DataType): The type of the column as :class:`.DataType`
        datasize(int): The size of the column
        bitfields(iter): For columns of bitfield type, define :class:`.Bitfield` specification

    Attributes:
        name(str): The name of the column
        idx(int): The index of the column
        dtype(DataType): The type of the column as :class:`.DataType`
        datasize(int): The size of the column
        bitfields(iter): For columns of bitfield type, define :class:`.Bitfield` specification
    """

    class Bitfield:
        """
        Specifies the meaning of the bits encoded in a column of type bitfield

        Parameters:
            name(str): Name of a group of bits
            size(int): Number of bits
            offset(int): Offset of bits within the decoded (integer) value

        Attributes:
            name(str): Name of a group of bits
            size(int): Number of bits
            offset(int): Offset of bits within the decoded (integer) value
        """

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

        assert (dtype == BITFIELD) != (len(bitfields) == 0)
        if self.bitfields:
            assert isinstance(self.bitfields, Iterable)
            assert all(isinstance(b, ColumnInfo.Bitfield) for b in self.bitfields)

    def __str__(self):
        if self.dtype == BITFIELD:
            bitfield_str = "(" + ",".join("{}:{}".format(b.name, b.size) for b in self.bitfields) + ")"
        else:
            bitfield_str = ""
        return "{}:{}{}".format(self.name, TYPE_NAMES.get(self.dtype, "<unknown>"), bitfield_str)

    def __repr__(self):
        return str(self)

    def __eq__(self, other):
        return (
            self.name == other.name
            and self.dtype == other.dtype
            and self.index == other.index
            and self.datasize == other.datasize  # This may be overzealous?
            and self.bitfields == other.bitfields
        )


class Frame:
    """
    Represent the decoded dataframe

    Parameters:
        source(str|file): A file-like object to decode the data from

    Attributes:
        properties(dict): Dictionary of additional properties that can contain arbitrary metadata
        columns(list): A list of :class:`.ColumnInfo` objects describing the column structure of the frame
        nrows(int): Number of rows of data within the frame
        ncolumns(int): Number of data columns within the frame
    """

    def __init__(self, source):
        # Read marker and magic

        m = source.read(2)
        if len(m) == 0:
            raise EOFError()
        assert int.from_bytes(m, byteorder="big", signed=False) == NEW_HEADER

        assert source.read(3) == MAGIC

        # Get byte ordering

        endian_marker = source.read(4)
        if int.from_bytes(endian_marker, byteorder="little") == ENDIAN_MARKER:
            stream = LittleEndianStream(source)
        else:
            stream = BigEndianStream(source)

        # TODO: Some inequalities here, rather than plain statement
        assert stream.readInt32() == FORMAT_VERSION_NUMBER_MAJOR
        assert stream.readInt32() == FORMAT_VERSION_NUMBER_MINOR

        # MD5 checksum
        assert stream.readString()

        headerLength = stream.readInt32()
        self._dataStartPosition = stream.position() + headerLength

        # 0 means we don't know offset of next header.

        self._dataSize = stream.readInt64()
        self._dataEndPosition = self._dataStartPosition + self._dataSize

        # prevFrameOffset
        assert stream.readInt64() == 0

        self._numberOfRows = stream.readInt64()

        self.flags = [stream.readReal64() for _ in range(stream.readInt32())]

        self.properties = {}

        for _ in range(stream.readInt32()):
            key = stream.readString()
            value = stream.readString()
            assert key not in self.properties
            self.properties[key] = value

        self._numberOfColumns = stream.readInt32()
        self._columnPosition = stream.position()

        self.__columnCodecs = None
        self._columns = None

        self._stream = stream

        # Support frame aggregation
        self._trailingAggregatedFrames = []

    def seekToEnd(self):
        self._stream.seek(self._dataEndPosition)

    @property
    def _column_codecs(self):
        """
        Internal method to get the codecs for the given column.
        These are read/constructed lazily from the file handle so that we can do scans through the file rapidly.

        Returns:
            list: A list of codecs
        """
        if self.__columnCodecs is None:
            self._stream.seek(self._columnPosition)
            self.__columnCodecs = [read_codec(self._stream) for _ in range(self._numberOfColumns)]
            assert self._stream.position() == self._dataStartPosition
        return self.__columnCodecs

    @property
    def columns(self):
        return [
            ColumnInfo(
                codec.column_name,
                idx,
                codec.type,
                codec.data_size,
                [
                    ColumnInfo.Bitfield(name=nm, size=sz, offset=off)
                    for nm, sz, off in zip(
                        codec.bitfield_names,
                        codec.bitfield_sizes,
                        accumulate(chain([0], codec.bitfield_sizes)),
                    )
                ],
            )
            for idx, codec in enumerate(self._column_codecs)
        ]

    @property
    def column_dict(self):
        return {c.name: c for c in self.columns}

    @property
    def simple_column_dict(self):
        return {c.name.split("@")[0]: c for c in self.columns}

    @property
    def nrows(self):
        return self._numberOfRows + sum(f.nrows for f in self._trailingAggregatedFrames)

    @property
    def ncolumns(self):
        if self.__columnCodecs is not None:
            assert self._numberOfColumns == len(self.__columnCodecs)
        return self._numberOfColumns

    def dataframe(self, columns=None):
        """
        Decodes the frame into a pandas dataframe

        Parameters:
            columns: List of columns to decode

        Returns:
            DataFrame
        """

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
                    # Once in here, we don't check if the column exists. If it doesn't this will show up later
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
        """
        Decodes the frame into a pandas dataframe

        Parameters:
            columns: List of columns to decode

        Returns:
            DataFrame
        """
        # TODO: Properly skip decoding columns that aren't needed
        column_codecs = self._column_codecs

        self._stream.seek(self._dataStartPosition)

        output_cols = [[] for _ in range(self._numberOfColumns)]

        # Select the correct output columns. Note we allow selection of fully-qualified
        # names, but we also allow selection of short names of the form <name>@<table> (so
        # long as these names are not ambiguous
        output = {}
        full_matches = set()
        for codec, output_col in zip(column_codecs, output_cols):
            if columns is None or codec.column_name in columns:
                output[codec.column_name] = output_col
                full_matches.add(codec.column_name)
            else:
                splitname = codec.column_name.split("@")
                if len(splitname) == 2:
                    name, table = splitname
                    if name in columns:
                        if name in output:
                            # If we have already matched "foo" against "foo", then "foo" matching "foo@bar" is
                            # a weaker match, not an ambiguity
                            if name in full_matches:
                                continue
                            raise KeyError("Ambiguous short column name '{}' requested".format(name))
                        output[name] = output_col

        if columns:
            for name in columns:
                if name not in output:
                    raise KeyError(f"Requested columns '{name}' not found")

        lastDecoded = [0] * self._numberOfColumns

        lastStartCol = None
        for row in range(self._numberOfRows):
            startCol = self._stream.readMarker()

            if lastStartCol is None:
                if startCol > 0:
                    for col in range(startCol):
                        output_cols[col].append(column_codecs[col].typed_missing_value)

            elif lastStartCol > startCol:
                for col in range(startCol, lastStartCol):
                    last = output_cols[col][-1]
                    output_cols[col].extend(last for _ in range(row - lastDecoded[col] - 1))

            lastStartCol = startCol

            for col in range(startCol, self._numberOfColumns):
                output_cols[col].append(column_codecs[col].decode(self._stream))
                lastDecoded[col] = row

        if lastStartCol is not None:
            for col in range(lastStartCol):
                last = output_cols[col][-1]
                output_cols[col].extend(last for _ in range(self._numberOfRows - lastDecoded[col] - 1))

        df = pd.DataFrame(output)

        if len(self._trailingAggregatedFrames) > 0:
            return pd.concat(
                [df] + [f._dataframe_internal(columns) for f in self._trailingAggregatedFrames],
                copy=False,
                axis=0,
                ignore_index=True,
            )
        else:
            return df

    def _append(self, frame: "Frame"):
        if self.column_dict != frame.column_dict:
            raise MismatchedFramesError
        self._trailingAggregatedFrames.append(frame)
