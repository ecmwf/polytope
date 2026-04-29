import json
import math
import os
import tempfile

import eccodes


def get_first_grib_message(req):
    import pyfdb

    fdb = pyfdb.FDB()

    # Make sure that we are accessing a single georef so that the grid is consistent
    assert 'georef' in req.keys()

    # Use data_handle from the list element directly instead of a separate
    # retrieve() call — avoids the list iterator polluting retrieve state.
    first_element = next(fdb.list(req))
    dh = first_element.data_handle
    if dh is None:
        raise ValueError('List element has no data handle')
    with dh:
        msg_bytes = dh.read()

    gid = eccodes.codes_new_from_message(msg_bytes)
    return gid


def get_gridspec_lamebert_conformal(gid):
    to_rad = math.pi / 180

    md5hash = eccodes.codes_get(gid, 'md5GridSection')

    earth_round = (eccodes.codes_get(gid, 'shapeOfTheEarth') == 0) or (eccodes.codes_get(gid, 'shapeOfTheEarth') == 6)

    if earth_round:
        if eccodes.codes_get(gid, 'shapeOfTheEarth') == 6:
            radius = 6371229
        elif eccodes.codes_get(gid, 'shapeOfTheEarth') == 0:
            radius = 6367470
    else:
        radius = None

    nv = eccodes.codes_get(gid, 'NV')
    nx = eccodes.codes_get(gid, 'Nx')
    ny = eccodes.codes_get(gid, 'Ny')
    LoVInDegrees = eccodes.codes_get(gid, 'LoV') / 1000000
    Dx = eccodes.codes_get(gid, 'Dx')
    Dy = eccodes.codes_get(gid, 'Dy')
    latFirstInRadians = eccodes.codes_get(gid, 'latitudeOfFirstGridPoint') / 1000000 * to_rad
    lonFirstInRadians = eccodes.codes_get(gid, 'longitudeOfFirstGridPoint') / 1000000 * to_rad
    LoVInRadians = eccodes.codes_get(gid, 'LoV') / 1000000 * to_rad
    Latin1InRadians = eccodes.codes_get(gid, 'Latin1') / 1000000 * to_rad
    Latin2InRadians = eccodes.codes_get(gid, 'Latin2') / 1000000 * to_rad
    LaDInRadians = eccodes.codes_get(gid, 'LaD') / 1000000 * to_rad

    gridspec = {
        'type': 'lambert_conformal',
        'earth_round': earth_round,
        'radius': radius,
        'nv': nv,
        'nx': nx,
        'ny': ny,
        'LoVInDegrees': LoVInDegrees,
        'Dx': Dx,
        'Dy': Dy,
        'latFirstInRadians': latFirstInRadians,
        'lonFirstInRadians': lonFirstInRadians,
        'LoVInRadians': LoVInRadians,
        'Latin1InRadians': Latin1InRadians,
        'Latin2InRadians': Latin2InRadians,
        'LaDInRadians': LaDInRadians,
    }
    return (gridspec, md5hash)


def get_gridspec_icon(gid):
    md5hash = eccodes.codes_get(gid, 'md5GridSection')
    gridspec = {}
    return (gridspec, md5hash)


def get_gridspec_and_hash(gid):
    grid_type = eccodes.codes_get(gid, 'gridType')
    if grid_type == 'lambert_lam':
        return get_gridspec_lamebert_conformal(gid)
    elif grid_type == 'icon':
        return get_gridspec_icon(gid)
    else:
        raise ValueError(f'Unsupported grid type: {grid_type}')


def _grid_cache_file():
    return os.path.join(os.path.dirname(__file__), 'grid_cache.json')


def _load_cache():
    try:
        with open(_grid_cache_file(), 'r', encoding='utf-8') as fh:
            return json.load(fh)
    except FileNotFoundError:
        return {}
    except Exception:
        return {}


def _save_cache(cache):
    grid_cache_file = _grid_cache_file()
    dirpath = os.path.dirname(grid_cache_file)
    os.makedirs(dirpath, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=dirpath, prefix='.grid_cache.')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as fh:
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


def lookup_grid_config_local(req):
    gid = get_first_grib_message(req)
    req_georef = req['georef']
    cache = _load_cache()
    cache_key = _cache_key(req_georef)

    try:
        if cache_key in cache:
            entry = cache[cache_key]
            return (entry.get('gridspec'), entry.get('md5hash'))

        gridspec, md5hash = get_gridspec_and_hash(gid)
        cache[cache_key] = {'gridspec': gridspec, 'md5hash': md5hash}
        try:
            _save_cache(cache)
        except Exception:
            pass
        return (gridspec, md5hash)
    finally:
        eccodes.codes_release(gid)
