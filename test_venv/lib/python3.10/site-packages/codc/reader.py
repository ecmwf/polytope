import io

import pandas

from .frame import Frame
from .lib import ffi, lib


class Reader:
    """This is the main container class for reading ODBs"""

    __reader = None
    __frames = None

    def __init__(self, source, aggregated=True, max_aggregated=-1):
        self.__aggregated = aggregated
        self.__max_aggregated = max_aggregated

        reader = ffi.new("odc_reader_t**")
        if isinstance(source, io.IOBase):
            lib.odc_open_file_descriptor(reader, source.fileno())
        else:
            assert isinstance(source, str)
            lib.odc_open_path(reader, source.encode())

        # Set free function
        self.__reader = ffi.gc(reader[0], lib.odc_close)

    @property
    def frames(self):
        if self.__frames is None:
            self.__frames = []

            frame = ffi.new("odc_frame_t**")
            lib.odc_new_frame(frame, self.__reader)
            frame = ffi.gc(frame[0], lib.odc_free_frame)
            while (
                lib.odc_next_frame_aggregated(frame, self.__max_aggregated)
                if self.__aggregated
                else lib.odc_next_frame(frame)
            ) != lib.ODC_ITERATION_COMPLETE:
                copy_frame = ffi.new("odc_frame_t**")
                lib.odc_copy_frame(frame, copy_frame)
                self.__frames.append(Frame(ffi.gc(copy_frame[0], lib.odc_free_frame)))

        return self.__frames


def _read_odb_generator(source, columns=None, aggregated=True, max_aggregated=-1):
    r = Reader(source, aggregated=aggregated, max_aggregated=max_aggregated)
    for f in r.frames:
        yield f.dataframe(columns)


def _read_odb_oneshot(source, columns=None):
    reduced = pandas.concat(_read_odb_generator(source, columns), sort=False, ignore_index=True)
    for name, data in reduced.items():
        if data.dtype == "object":
            data.where(pandas.notnull(data), None, inplace=True)
    return reduced


def read_odb(source, columns=None, aggregated=True, single=False, max_aggregated=-1):
    if single:
        assert aggregated
        return _read_odb_oneshot(source, columns)
    else:
        return _read_odb_generator(source, columns, aggregated, max_aggregated)
