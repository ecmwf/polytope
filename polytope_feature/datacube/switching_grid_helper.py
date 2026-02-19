import json
import math
import os
import tempfile

import eccodes
import pyfdb

# from polytope_feature.options import MapperConfig


def get_first_grib_message(req):
    fdb = pyfdb.FDB()

    # Make sure that we are accessing a single georef so that the grid is consistent
    assert "georef" in req.keys()

    first_field = next(fdb.list(req, keys=True))["keys"]

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
    return gid


def get_gridspec_lamebert_conformal(gid):
    # Lambert lam grid

    to_rad = math.pi / 180

    md5hash = eccodes.codes_get(gid, "md5GridSection")

    earth_round = (eccodes.codes_get(gid, "shapeOfTheEarth") == 0) or (
        eccodes.codes_get(gid, "shapeOfTheEarth") == 6
    )

    if earth_round:
        if eccodes.codes_get(gid, "shapeOfTheEarth") == 6:
            radius = 6371229
        elif eccodes.codes_get(gid, "shapeOfTheEarth") == 0:
            radius = 6367470
    else:
        # TODO: set the earth major and minor axis accordingly
        pass

    nv = eccodes.codes_get(gid, "NV")
    nx = eccodes.codes_get(gid, "Nx")
    ny = eccodes.codes_get(gid, "Ny")
    LoVInDegrees = eccodes.codes_get(gid, "LoV") / 1000000
    Dx = eccodes.codes_get(gid, "Dx")
    Dy = eccodes.codes_get(gid, "Dy")
    latFirstInRadians = (
        eccodes.codes_get(gid, "latitudeOfFirstGridPoint") / 1000000 * to_rad
    )
    lonFirstInRadians = (
        eccodes.codes_get(gid, "longitudeOfFirstGridPoint") / 1000000 * to_rad
    )
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
    # ICON
    # TODO: Need the following:
    # uuid: Optional[str] = None
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


# TODO: extract the right info and then write it to file, one for the grid hash and one for the actual config


def lookup_grid_config(req):
    gid = get_first_grib_message(req)
    req_georef = req["georef"]

    # Cache file stored alongside this module
    GRID_CACHE_FILE = os.path.join(os.path.dirname(__file__), "grid_cache.json")

    def _load_cache():
        try:
            with open(GRID_CACHE_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except FileNotFoundError:
            return {}
        except Exception:
            return {}

    def _save_cache(cache):
        dirpath = os.path.dirname(GRID_CACHE_FILE)
        os.makedirs(dirpath, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=dirpath, prefix=".grid_cache.")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(cache, fh, indent=2, sort_keys=True)
            os.replace(tmp, GRID_CACHE_FILE)
        finally:
            if os.path.exists(tmp):
                try:
                    os.remove(tmp)
                except Exception:
                    pass

    # Use a stable serialization of the georef as the cache key
    try:
        cache_key = json.dumps(req_georef, sort_keys=True, default=str)
    except Exception:
        cache_key = str(req_georef)

    cache = _load_cache()

    try:
        if cache_key in cache:
            entry = cache[cache_key]
            return (entry.get("gridspec"), entry.get("md5hash"))

        gridspec, md5hash = get_gridspec_and_hash(gid)
        cache[cache_key] = {"gridspec": gridspec, "md5hash": md5hash}
        try:
            _save_cache(cache)
        except Exception:
            # Swallow cache write errors but continue to return computed value
            pass
        return (gridspec, md5hash)
    finally:
        eccodes.codes_release(gid)


# def gridspec_to_grid_config(gridspec, md5hash):
#     if gridspec.get("type") == "lambert_conformal":
#         mc = MapperConfig(
#             name="mapper",
#             type="lambert_conformal",
#             md5_hash=md5hash,
#             is_spherical=gridspec.get("earth_round"),
#             radius=gridspec.get("radius"),
#             nv=gridspec.get("nv"),
#             nx=gridspec.get("nx"),
#             ny=gridspec.get("ny"),
#             LoVInDegrees=gridspec.get("LoVInDegrees"),
#             Dx=gridspec.get("Dx"),
#             Dy=gridspec.get("Dy"),
#             latFirstInRadians=gridspec.get("latFirstInRadians"),
#             lonFirstInRadians=gridspec.get("lonFirstInRadians"),
#             LoVInRadians=gridspec.get("LoVInRadians"),
#             Latin1InRadians=gridspec.get("Latin1InRadians"),
#             Latin2InRadians=gridspec.get("Latin2InRadians"),
#             LaDInRadians=gridspec.get("LaDInRadians"),
#         )
#         return mc
#     return None

# def replace_grid_config_in_options(options, req):
#     gridspec, md5hash = lookup_grid_config(req)
#     grid_config = gridspec_to_grid_config(gridspec, md5hash)
#     if grid_config is not None:
#         for axis_conf in options.axis_config:
#             for idx, transformation in enumerate(axis_conf.transformations):
#                 if getattr(transformation, "name", None) == "mapper":
#                     axis_conf.transformations[idx] = grid_config
#                     return True
#     return False
