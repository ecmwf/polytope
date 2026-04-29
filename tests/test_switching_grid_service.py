import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

from polytope_feature.datacube.switching_grid_helper import lookup_grid_config, lookup_grid_config_remote
from polytope_feature.options import PolytopeOptions


class _MockHandler(BaseHTTPRequestHandler):
    response_payload = {
        'gridspec': {
            'type': 'lambert_conformal',
            'earth_round': True,
            'radius': 6371229,
            'nv': 0,
            'nx': 10,
            'ny': 20,
            'LoVInDegrees': 1.0,
            'Dx': 1000.0,
            'Dy': 1000.0,
            'latFirstInRadians': 0.1,
            'lonFirstInRadians': 0.2,
            'LoVInRadians': 0.3,
            'Latin1InRadians': 0.4,
            'Latin2InRadians': 0.5,
            'LaDInRadians': 0.6,
        },
        'md5hash': 'abc123',
    }
    seen_request = None

    def do_POST(self):
        length = int(self.headers.get('Content-Length', '0'))
        payload = json.loads(self.rfile.read(length).decode('utf-8'))
        _MockHandler.seen_request = payload
        body = json.dumps(_MockHandler.response_payload).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        return


class _MockServer:
    def __enter__(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), _MockHandler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        host, port = self.server.server_address
        self.url = f'http://{host}:{port}'
        return self.url

    def __exit__(self, exc_type, exc, tb):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)


def test_lookup_grid_config_remote_service():
    req = {'georef': 'u1516b', 'class': 'd1'}
    with _MockServer() as url:
        gridspec, md5hash = lookup_grid_config(req, service_url=url)

    assert md5hash == 'abc123'
    assert gridspec['type'] == 'lambert_conformal'
    assert _MockHandler.seen_request == {'request': req}


def test_lookup_grid_config_remote_retries_on_timeout(monkeypatch):
    req = {'georef': 'u1516b', 'class': 'd1'}
    calls = []

    class _Response:
        def raise_for_status(self):
            return None

        def json(self):
            return _MockHandler.response_payload

    def _fake_post(url, json, timeout):
        calls.append(timeout)
        if len(calls) == 1:
            raise requests.Timeout('slow first attempt')
        return _Response()

    monkeypatch.setattr(requests, 'post', _fake_post)

    gridspec, md5hash = lookup_grid_config_remote(req, 'http://example.com')

    assert md5hash == 'abc123'
    assert gridspec['type'] == 'lambert_conformal'
    assert calls == [1.0, 5.0]


def test_dynamic_grid_service_replaces_mapper_config():
    options = {
        'axis_config': [
            {
                'axis_name': 'values',
                'transformations': [
                    {'name': 'mapper', 'type': 'reduced_gaussian', 'resolution': 320, 'axes': ['latitude', 'longitude']}
                ],
            }
        ],
        'compressed_axes_config': ['longitude', 'latitude'],
        'pre_path': {'class': 'd1', 'georef': 'u1516b'},
        'dynamic_grid': True,
    }

    with _MockServer() as url:
        options['dynamic_grid_service_url'] = url
        axis_config, *_ = PolytopeOptions.get_polytope_options(options)

    mapper = axis_config[0].transformations[0]
    assert mapper.name == 'mapper'
    assert mapper.type == 'lambert_conformal'
    assert mapper.md5_hash == 'abc123'
    assert mapper.axes == ['latitude', 'longitude']
