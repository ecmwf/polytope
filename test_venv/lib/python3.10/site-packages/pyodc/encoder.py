import hashlib
import io

import numpy as np
import pandas as pd

from .codec import select_codec
from .constants import ENDIAN_MARKER, FORMAT_VERSION_NUMBER_MAJOR, FORMAT_VERSION_NUMBER_MINOR, MAGIC, NEW_HEADER
from .stream import BigEndianStream, LittleEndianStream


def encode_odb(
    dataframe: pd.DataFrame,
    target,
    rows_per_frame=10000,
    types: dict = None,
    bigendian: bool = False,
    properties: dict = None,
    bitfields: dict = None,
):
    """
    Encode a pandas dataframe into an ODB-2 stream

    Parameters:
        dataframe(DataFrame): A pandas dataframe to encode
        target(str|file): A file-like object to write the encoded data to
        types(dict): A dictionary of (optional) column-name : constant :class:`.DataType` pairs, or ``None``
        bigendian(bool): Encode in big-endian byte order if ``True``
        properties(dict): Encode a dictionary of supplied properties
        bitfields(dict): A dictionary containing entries for BITFIELD columns. The values are either bitfield names, or
                         tuple pairs of bitfield name and bitfield size
    """
    if isinstance(target, str):
        with open(target, "wb") as real_target:
            return encode_odb(
                dataframe,
                real_target,
                rows_per_frame=rows_per_frame,
                types=types,
                bigendian=bigendian,
                properties=properties,
                bitfields=bitfields,
            )

    column_order = None

    # Split the dataframe into chunks of appropriate size
    for i, sub_df in dataframe.groupby(np.arange(len(dataframe)) // rows_per_frame):
        column_order = encode_single_dataframe(
            sub_df,
            target,
            types=types,
            column_order=column_order,
            bigendian=bigendian,
            properties=(properties or {}),
            bitfields=bitfields,
        )


def encode_single_dataframe(
    dataframe: pd.DataFrame,
    target,
    types: dict = None,
    column_order: list = None,
    bigendian: bool = False,
    properties: dict = None,
    bitfields: dict = None,
):
    """
    Encode a single dataframe into an ODB-2 stream

    Parameters:
        dataframe(DataFrame): A pandas dataframe to encode
        target(str|file): A file-like object to write the encoded data to
        types(dict): A dictionary of (optional) column-name : constant :class:`.DataType` pairs, or ``None``
        column_order(list): A list of column names specifying the encode order. If ``None``, optimise according
                            to the rate of value changes in the columns
        bigendian(bool): Encode in big-endian byte order if ``True``
        properties(dict): Encode a dictionary of supplied properties
        bitfields(dict): A dictionary containing entries for BITFIELD columns. The values are either bitfield names, or
                         tuple pairs of bitfield name and bitfield size

    Returns:
        list: The column order used for encoding as a list of column names

    :meta private:
    """

    stream_class = BigEndianStream if bigendian else LittleEndianStream

    codecs = [
        select_codec(name, data, (types or {}).get(name, None), (bitfields or {}).get(name, None))
        for name, data in dataframe.items()
    ]

    # If a column order has been specified, sort the codecs according to it. otherwise sort
    # the codecs for the most efficient use of the given data

    if column_order:
        assert len(column_order) == len(set(column_order))
        assert set(column_order) == set(c.column_name for c in codecs)
        codecs = {c.column_name: c for c in codecs}
        codecs = [codecs[column_name] for column_name in column_order]
    else:
        codecs.sort(key=lambda c: c.numChanges)
        column_order = [c.column_name for c in codecs]
        assert len(column_order) == len(set(column_order))

    data = _encodeData(dataframe, codecs, stream_class)
    headerPart2 = _encodeHeaderPart2(dataframe, codecs, stream_class, len(data), (properties or {}))
    headerPart1 = _encodeHeaderPart1(headerPart2, stream_class)

    target.write(headerPart1)
    target.write(headerPart2)
    target.write(data)

    return column_order


def _encodeData(dataframe, codecs, stream_class):
    """
    Encode the data into a memory buffer
    """
    dataIO = io.BytesIO()
    stream = stream_class(dataIO)

    # Encode the column in the order supplied in the indexes list, rather than that
    # inherent in the dataframe.

    column_indexes = {column_name: i for i, column_name in enumerate(dataframe.columns)}
    column_indexes = [column_indexes[codec.column_name] for codec in codecs]

    # Iterate over rows

    last_row = None
    codec_indexes = list(zip(codecs, column_indexes))

    for row in dataframe.itertuples(index=False):
        for i, (codec, index) in enumerate(codec_indexes):
            if last_row is None or (
                row[index] != last_row[index] and not (pd.isnull(row[index]) and pd.isnull(last_row[index]))
            ):
                break

        stream.encodeMarker(i)

        for codec, index in codec_indexes[i:]:
            codec.encode(stream, row[index])

        last_row = row

    return dataIO.getbuffer()


def _encodeHeaderPart2(dataframe, codecs, stream_class, data_len, properties):
    """
    Encode the second part of the header - whose size and md5 is required to encode
    the first part of the header.
    """
    headerIO = io.BytesIO()
    stream = stream_class(headerIO)

    # Data Size (nextFrameOffset)
    stream.encodeInt64(data_len)

    # prevFrameOffset = 0
    stream.encodeInt64(0)

    # Number of rows
    stream.encodeInt64(dataframe.shape[0])

    # Flags... --> Currently no flags, no properties (remember to update Header Length)
    stream.encodeInt32(0)

    # Externally specified properties
    stream.encodeInt32(len(properties))
    for k, v in properties.items():
        stream.encodeString(k)
        stream.encodeString(v)

    # Number of columns
    stream.encodeInt32(dataframe.shape[1])

    # Encode the codec information
    for codec in codecs:
        codec.encode_header(stream)

    return headerIO.getbuffer()


def _encodeHeaderPart1(headerPart2, stream_class):
    """
    Encode the first part of the header. This _could_ be done directly
    on the file-like object, although that would incurr many more filesystem
    operations.
    """
    headerIO = io.BytesIO()
    stream = stream_class(headerIO)

    stream.encodeMarker(NEW_HEADER)
    stream.write(MAGIC)

    stream.encodeInt32(ENDIAN_MARKER)

    stream.encodeInt32(FORMAT_VERSION_NUMBER_MAJOR)
    stream.encodeInt32(FORMAT_VERSION_NUMBER_MINOR)

    # MD5
    m = hashlib.md5()
    m.update(headerPart2)
    md = m.hexdigest()
    stream.encodeString(md)

    # Header Length
    stream.encodeInt32(len(headerPart2))

    return headerIO.getbuffer()
