import json
import math
import os
import tempfile
import threading

import eccodes

_GRID_CACHE = None
_GRID_CACHE_LOCK = threading.Lock()
_DEFAULT_MAX_GRIB_MESSAGE_BYTES = 512 * 1024 * 1024


def _max_grib_message_bytes():
    return int(os.environ.get("POLYTOPE_MAX_GRIB_MESSAGE_BYTES", _DEFAULT_MAX_GRIB_MESSAGE_BYTES))


def _read_exact(data_handle, length):
    buffer = bytearray(length)
    view = memoryview(buffer)
    offset = 0

    while offset < length:
        if hasattr(data_handle, "readinto"):
            bytes_read = data_handle.readinto(view[offset:])
        else:
            chunk = data_handle.read(length - offset)
            bytes_read = len(chunk)
            view[offset : offset + bytes_read] = chunk

        if bytes_read <= 0:
            raise EOFError(f"Short GRIB read: wanted {length} bytes, got {offset}")
        offset += bytes_read

    return bytes(buffer)


def _validate_grib_message(message):
    if len(message) < 8:
        raise EOFError(f"Short GRIB read: wanted at least 8 bytes, got {len(message)}")

    header = message[:8]

    if header[:4] != b"GRIB":
        raise ValueError("Not a GRIB message")

    edition = header[7]
    if edition == 1:
        total_length = int.from_bytes(header[4:7], "big")
        header_length = 8
    elif edition == 2:
        if len(message) < 16:
            raise EOFError(f"Short GRIB read: wanted at least 16 bytes, got {len(message)}")
        header = message[:16]
        total_length = int.from_bytes(header[8:16], "big")
        header_length = 16
    else:
        raise ValueError(f"Unsupported GRIB edition: {edition}")

    if total_length < header_length:
        raise ValueError(f"Invalid GRIB length: {total_length}")

    max_length = _max_grib_message_bytes()
    if total_length > max_length:
        raise ValueError(f"GRIB message length {total_length} exceeds maximum {max_length}")

    if len(message) < total_length:
        raise EOFError(f"Short GRIB read: wanted {total_length} bytes, got {len(message)}")

    grib_message = message[:total_length]
    if grib_message[-4:] != b"7777":
        raise ValueError("GRIB terminator missing")

    return grib_message


def read_first_grib_message(data_handle, data_length):
    if data_length <= 0:
        raise ValueError(f"Invalid data handle length: {data_length}")

    max_length = _max_grib_message_bytes()
    if data_length > max_length:
        raise ValueError(f"Data handle length {data_length} exceeds maximum {max_length}")

    return _validate_grib_message(_read_exact(data_handle, data_length))


def get_first_grib_message(req):
    import pyfdb

    fdb = pyfdb.FDB()

    # Use data_handle from the list element directly instead of a separate
    # retrieve() call — avoids the list iterator polluting retrieve state.
    first_element = next(fdb.list(req))
    dh = first_element.data_handle
    if dh is None:
        raise ValueError("List element has no data handle")
    with dh:
        msg_bytes = read_first_grib_message(dh, first_element.length())

    gid = eccodes.codes_new_from_message(msg_bytes)
    return gid


def get_gridspec_lamebert_conformal(gid):
    to_rad = math.pi / 180

    md5hash = eccodes.codes_get(gid, "md5GridSection")

    earth_round = (eccodes.codes_get(gid, "shapeOfTheEarth") == 0) or (eccodes.codes_get(gid, "shapeOfTheEarth") == 6)

    if earth_round:
        if eccodes.codes_get(gid, "shapeOfTheEarth") == 6:
            radius = 6371229
        elif eccodes.codes_get(gid, "shapeOfTheEarth") == 0:
            radius = 6367470
    else:
        radius = None

    nv = eccodes.codes_get(gid, "NV")
    nx = eccodes.codes_get(gid, "Nx")
    ny = eccodes.codes_get(gid, "Ny")
    LoVInDegrees = eccodes.codes_get(gid, "LoV") / 1000000
    Dx = eccodes.codes_get(gid, "Dx")
    Dy = eccodes.codes_get(gid, "Dy")
    latFirstInRadians = eccodes.codes_get(gid, "latitudeOfFirstGridPoint") / 1000000 * to_rad
    lonFirstInRadians = eccodes.codes_get(gid, "longitudeOfFirstGridPoint") / 1000000 * to_rad
    LoVInRadians = eccodes.codes_get(gid, "LoV") / 1000000 * to_rad
    Latin1InRadians = eccodes.codes_get(gid, "Latin1") / 1000000 * to_rad
    Latin2InRadians = eccodes.codes_get(gid, "Latin2") / 1000000 * to_rad
    LaDInRadians = eccodes.codes_get(gid, "LaD") / 1000000 * to_rad

    gridspec = {
        "type": "lambert_conformal",
        "earth_round": earth_round,
        "radius": radius,
        "nv": nv,
        "nx": nx,
        "ny": ny,
        "LoVInDegrees": LoVInDegrees,
        "Dx": Dx,
        "Dy": Dy,
        "latFirstInRadians": latFirstInRadians,
        "lonFirstInRadians": lonFirstInRadians,
        "LoVInRadians": LoVInRadians,
        "Latin1InRadians": Latin1InRadians,
        "Latin2InRadians": Latin2InRadians,
        "LaDInRadians": LaDInRadians,
    }
    return (gridspec, md5hash)


def get_gridspec_icon(gid):
    md5hash = eccodes.codes_get(gid, "md5GridSection")
    gridspec = {}
    return (gridspec, md5hash)


def get_gridspec_and_hash(gid):
    grid_type = eccodes.codes_get(gid, "gridType")
    if grid_type == "lambert_lam":
        return get_gridspec_lamebert_conformal(gid)
    elif grid_type == "icon":
        return get_gridspec_icon(gid)
    else:
        raise ValueError(f"Unsupported grid type: {grid_type}")


def _grid_cache_file():
    return os.path.join(os.path.dirname(__file__), "grid_cache.json")


def _load_cache():
    try:
        with open(_grid_cache_file(), "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _save_cache(cache):
    grid_cache_file = _grid_cache_file()
    dirpath = os.path.dirname(grid_cache_file)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=".grid_cache.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(cache, fh, indent=2, sort_keys=True)
        os.replace(tmp, grid_cache_file)
    finally:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except Exception:
                pass


def _cache_key(req_georef):
    try:
        return json.dumps(req_georef, sort_keys=True, default=str)
    except Exception:
        return str(req_georef)


def _get_cache_locked():
    global _GRID_CACHE
    if _GRID_CACHE is None:
        _GRID_CACHE = _load_cache()
    return _GRID_CACHE


def lookup_grid_config_local(req):
    # Make sure that we are accessing a single georef so that the grid is consistent
    if "georef" not in req.keys():
        return
    req_georef = req["georef"]
    cache_key = _cache_key(req_georef)

    with _GRID_CACHE_LOCK:
        cache = _get_cache_locked()
        if cache_key in cache:
            entry = cache[cache_key]
            return (entry.get("gridspec"), entry.get("md5hash"))

    gid = get_first_grib_message(req)
    try:
        gridspec, md5hash = get_gridspec_and_hash(gid)
    finally:
        eccodes.codes_release(gid)

    with _GRID_CACHE_LOCK:
        cache = _get_cache_locked()
        if cache_key in cache:
            entry = cache[cache_key]
            return (entry.get("gridspec"), entry.get("md5hash"))

        cache[cache_key] = {"gridspec": gridspec, "md5hash": md5hash}
        try:
            _save_cache(cache)
        except Exception:
            pass
        return (gridspec, md5hash)
