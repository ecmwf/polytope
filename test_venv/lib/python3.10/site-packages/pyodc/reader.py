import io

import pandas

from .frame import Frame, MismatchedFramesError


class Reader:
    """
    An object that owns the input data stream, and splits it into a sequence of frames that can be interrogated

    Parameters:
        source(str|file): A file-like object to decode the data from
        aggregated(bool): Group result into logical dataframes if ``True``

    Attributes:
        frames(DataFrame): Decoded dataframes
    """

    def __init__(self, source, aggregated=True):
        self.__aggregated = aggregated
        self._frames = []

        if isinstance(source, io.IOBase):
            self._f = source
        else:
            self._f = open(source, "rb")

        while True:
            try:
                self._frames.append(Frame(self._f))
                self._frames[-1].seekToEnd()
            except EOFError:
                # n.b. f.read() does not throw EOFError, so this will only catch the exception
                # thrown internally when the table marker is not found
                break

        if self.__aggregated:
            if len(self._frames) > 1:
                aggregated_frames = [self._frames[0]]
                for frame in self._frames[1:]:
                    try:
                        aggregated_frames[-1]._append(frame)
                    except MismatchedFramesError:
                        aggregated_frames.append(frame)
                self._frames = aggregated_frames

    @property
    def frames(self):
        return self._frames


def _read_odb_generator(source, columns=None, aggregated=True):
    r = Reader(source, aggregated=aggregated)
    for f in r.frames:
        yield f.dataframe(columns)


def _read_odb_oneshot(source, columns=None):
    reduced = pandas.concat(_read_odb_generator(source, columns), sort=False, ignore_index=True)
    for name, data in reduced.items():
        if data.dtype == "object":
            data.where(pandas.notnull(data), None, inplace=True)
    return reduced


def read_odb(source, columns=None, aggregated=True, single=False):
    """
    Decode an ODB-2 stream into a pandas dataframe

    Parameters:
        source(str|file): A file-like object to decode the data from
        columns(list|tuple): A list or a tuple of columns to decode
        aggregated(bool): Group result into logical dataframes if ``True``
        single(bool): Group result into a single dataframe if ``True`` and possible

    Returns:
        DataFrame
    """
    if single:
        assert aggregated
        return _read_odb_oneshot(source, columns)
    else:
        return _read_odb_generator(source, columns, aggregated)
