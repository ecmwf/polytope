import os
from urllib.parse import urljoin

import requests


def lookup_grid_config_local(req):
    from polytope_feature.datacube.switching_grid_local import lookup_grid_config_local as _lookup_grid_config_local

    return _lookup_grid_config_local(req)


def lookup_grid_config_remote(req, service_url, timeout=None, retries=None, retry_timeout=None):
    url = urljoin(service_url.rstrip('/') + '/', 'lookup-grid-config')
    if timeout is None:
        timeout = float(os.environ.get('POLYTOPE_DYNAMIC_GRID_SERVICE_TIMEOUT', '1'))
    if retries is None:
        retries = int(os.environ.get('POLYTOPE_DYNAMIC_GRID_SERVICE_RETRIES', '1'))
    if retry_timeout is None:
        retry_timeout = float(os.environ.get('POLYTOPE_DYNAMIC_GRID_SERVICE_RETRY_TIMEOUT', '5'))

    timeouts = [timeout] + [retry_timeout] * retries
    last_error = None
    for request_timeout in timeouts:
        try:
            response = requests.post(url, json={'request': req}, timeout=request_timeout)
            response.raise_for_status()
            payload = response.json()
            return (payload['gridspec'], payload['md5hash'])
        except (requests.Timeout, requests.ConnectionError) as exc:
            last_error = exc

    if last_error is not None:
        raise last_error
    raise RuntimeError('dynamic grid remote lookup failed without a captured error')


def lookup_grid_config(req, service_url=None):
    service_url = service_url or os.environ.get('POLYTOPE_DYNAMIC_GRID_SERVICE_URL')
    if service_url:
        return lookup_grid_config_remote(req, service_url)
    return lookup_grid_config_local(req)
