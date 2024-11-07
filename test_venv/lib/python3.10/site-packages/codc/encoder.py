import pandas

from .constants import BITFIELD, DOUBLE, INTEGER, STRING
from .lib import ffi, lib


def encode_odb(
    df: pandas.DataFrame, f, types: dict = None, rows_per_frame=10000, properties=None, bitfields: dict = None, **kwargs
):
    """
    Encode a pandas dataframe into ODB2 format

    :param df: The dataframe to encode
    :param f: The file-like object into which to encode the ODB2 data
    :param types: An optional (sparse) dictionary. Each key-value pair maps the name of a column to
                  encode to an ODB2 data type to use to encode it.
    :param rows_per_frame: The maximum number of rows to encode per frame. If this number is exceeded,
                           a sequence of frames will be encoded
    :param bitfields: A dictionary containing entries for BITFIELD columns. The values are either bitfield names, or
                      tuple pairs of bitfield name and bitfield size
    :param kwargs: Accept extra arguments that may be used by the python pyodc encoder.
    :return:
    """
    if isinstance(f, str):
        with open(f, "wb") as freal:
            return encode_odb(df, freal, types=types, rows_per_frame=rows_per_frame, properties=properties, **kwargs)

    # Some constants that are useful

    pmissing_integer = ffi.new("long*")
    pmissing_double = ffi.new("double*")
    lib.odc_missing_integer(pmissing_integer)
    lib.odc_missing_double(pmissing_double)
    missing_integer = pmissing_integer[0]
    missing_double = pmissing_double[0]

    def infer_column_type(arr, override_type):
        """
        Given a column of data, infer the encoding type.
        :param arr: The column of data to encode
        :param override_type:
        :return: (return_arr, dtype)
            - return_arr is the column of data to encode. This may be of a different internal type/contents
              to that supplied to the function, but it will normally not be.
            - The ODB2 type to encode with.
        """
        return_arr = arr
        dtype = override_type

        # Infer the column type from the data, if no column type given

        if dtype is None:
            if arr.dtype in ("uint64", "int64"):
                dtype = INTEGER
            elif arr.dtype == "float64":
                if not data.isnull().all() and all(pandas.isnull(v) or float(v).is_integer() for v in arr):
                    dtype = INTEGER
                else:
                    dtype = DOUBLE
            if arr.dtype == "object" or pandas.api.types.is_string_dtype(arr):
                if not arr.isnull().all() and all(s is None or isinstance(s, str) for s in arr):
                    dtype = STRING
                elif arr.isnull().all():
                    dtype = INTEGER

        # With an inferred, or supplied column type, massage the data into a form that can be encoded

        if arr.dtype == "object" or pandas.api.types.is_string_dtype(arr):
            # Map strings into an array that can be read in C
            if dtype == STRING:
                return_arr = return_arr.astype("|S{}".format(max(8, 8 * (1 + ((max(len(s) for s in arr) - 1) // 8)))))
            elif dtype == INTEGER or dtype == BITFIELD:
                return_arr = return_arr.fillna(value=missing_integer).astype("int64")

        elif arr.dtype == "float64":
            if dtype == INTEGER or dtype == BITFIELD:
                return_arr = arr.fillna(value=missing_integer).astype("int64")
            else:
                return_arr = arr.fillna(value=missing_double)

        if dtype is None:
            raise ValueError("Unsupported value type: {}".format(arr.dtype))

        return return_arr, dtype

    nrows = df.shape[0]
    if types is None:
        types = {}

    encoder = ffi.new("odc_encoder_t**")
    lib.odc_new_encoder(encoder)
    encoder = ffi.gc(encoder[0], lib.odc_free_encoder)

    for k, v in (properties or {}).items():
        lib.odc_encoder_add_property(encoder, k.encode("utf-8"), v.encode("utf-8"))

    lib.odc_encoder_set_row_count(encoder, nrows)
    lib.odc_encoder_set_rows_per_frame(encoder, rows_per_frame)

    # We store all of the numpy arrays here. Mostly this is just another reference to an
    # existing array, but some of the types require us to create a new (casted) copy, so
    # we need to put it somewhere to ensure it stays alive appropriately long.
    data_cache = []

    for i, (name, data) in enumerate(df.items()):
        data, dtype = infer_column_type(data, types.get(name, None))
        data_cache.append(data)

        lib.odc_encoder_add_column(encoder, str(name).encode("utf-8"), dtype)
        lib.odc_encoder_column_set_data_array(
            encoder,
            i,
            data.dtype.itemsize,
            data.array.to_numpy().strides[0],
            ffi.cast("void*", data.values.ctypes.data),
        )

        if bitfields and name in bitfields:
            for bf in bitfields[name]:
                nm = bf if isinstance(bf, str) else bf[0]
                sz = 1 if isinstance(bf, str) else bf[1]
                lib.odc_encoder_column_add_bitfield(encoder, i, nm.encode("utf-8"), sz)

    lib.odc_encode_to_file_descriptor(encoder, f.fileno(), ffi.NULL)
