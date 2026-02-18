import eccodes
import pyfdb

fdb = pyfdb.FDB()

req = {
    "class": "d1",
    "dataset": "on-demand-extremes-dt",
    "expver": "aac6",
    "stream": "oper",
    "type": "fc",
    "levtype": "ml",
    "georef": "u09tvk",
}

# Make sure that we are accessing a single georef so that the grid is consistent
assert "georef" in req.keys()

first_field = next(fdb.list(req, keys=True))["keys"]
print(first_field)

# for el in fdb.list(req, keys=True):
#     print(el["keys"])

field = fdb.retrieve(first_field)

# Normalize the retrieve() result into a plain `bytes` object
if hasattr(field, "read"):
    # file-like object: read the contents
    data = field.read()
else:
    data = field

# Convert common buffer types to bytes
if isinstance(data, bytes):
    msg_bytes = data
elif isinstance(data, bytearray):
    msg_bytes = bytes(data)
elif isinstance(data, memoryview):
    msg_bytes = data.tobytes()
else:
    # last resort: try to construct bytes (may raise)
    try:
        msg_bytes = bytes(data)
    except Exception as e:
        raise TypeError(f"Unsupported GRIB message type: {type(data)!r}") from e

gid = eccodes.codes_new_from_message(msg_bytes)

# We have two known grids we want to be able to generate
if eccodes.codes_get(gid, "gridType") == "lambert_lam":
    # Lambert lam grid
    # TODO
    # Need the following:
    # LoVInDegrees: Optional[float] = None
    # Dx: Optional[float] = None
    # Dy: Optional[float] = None
    # latFirstInRadians: Optional[float] = None
    # lonFirstInRadians: Optional[float] = None
    # LoVInRadians: Optional[float] = None
    # Latin1InRadians: Optional[float] = None
    # Latin2InRadians: Optional[float] = None
    # LaDInRadians: Optional[float] = None

    md5hash = eccodes.codes_get(gid, "md5GridSection")

    earth_round = (eccodes.codes_get(gid, "shapeOfTheEarth") == 0) or (
        eccodes.codes_get(gid, "shapeOfTheEarth") == 6
    )

    if earth_round:
        # TODO: set the radius accordingly
        pass
    else:
        # TODO: set the earth major and minor axis accordingly
        pass

    nv = eccodes.codes_get(gid, "NV")
    nx = eccodes.codes_get(gid, "Nx")
    ny = eccodes.codes_get(gid, "Ny")

    # print(eccodes.codes_dump(gid))

elif eccodes.codes_get(gid, "gridType") == "icon":
    # ICON
    # TODO
    # Need the following:
    # uuid: Optional[str] = None
    pass

# TODO: extract the right info and then write it to file, one for the grid hash and one for the actual config

eccodes.codes_release(gid)
