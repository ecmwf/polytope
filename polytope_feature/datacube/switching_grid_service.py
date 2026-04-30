import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from polytope_feature.datacube.switching_grid_local import lookup_grid_config_local

LOGGER = logging.getLogger(__name__)


class SwitchingGridHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        try:
            self.send_response(status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except BrokenPipeError:
            LOGGER.warning('client disconnected before response could be sent')
        except OSError:
            LOGGER.exception('failed to send HTTP response')

    def do_POST(self):
        if self.path.rstrip('/') != '/lookup-grid-config':
            LOGGER.warning('unknown POST path: %s', self.path)
            self._send_json(404, {'error': 'not found'})
            return

        try:
            content_length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode('utf-8') or '{}')
            req = payload.get('request', payload)
            LOGGER.info('lookup-grid-config request received for georef=%s', req.get('georef', 'unknown'))
            gridspec, md5hash = lookup_grid_config_local(req)
            self._send_json(200, {'gridspec': gridspec, 'md5hash': md5hash})
            LOGGER.info('lookup-grid-config request succeeded for georef=%s', req.get('georef', 'unknown'))
        except json.JSONDecodeError:
            LOGGER.warning('invalid JSON payload received')
            self._send_json(400, {'error': 'invalid JSON payload'})
        except (AssertionError, KeyError, ValueError) as exc:
            LOGGER.warning('bad lookup-grid-config request: %s', exc)
            self._send_json(400, {'error': str(exc)})
        except Exception as exc:
            LOGGER.exception('lookup-grid-config failed')
            self._send_json(500, {'error': str(exc)})

    def do_GET(self):
        if self.path.rstrip('/') == '/healthz':
            LOGGER.debug('health check requested')
            self._send_json(200, {'ok': True})
            return
        LOGGER.warning('unknown GET path: %s', self.path)
        self._send_json(404, {'error': 'not found'})

    def log_message(self, format, *args):
        LOGGER.info('%s - %s', self.address_string(), format % args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    server = ThreadingHTTPServer((args.host, args.port), SwitchingGridHandler)
    LOGGER.info('Starting switching-grid service on %s:%s', args.host, args.port)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        LOGGER.info('Stopping switching-grid service')
    finally:
        server.server_close()
        LOGGER.info('Switching-grid service stopped')


if __name__ == '__main__':
    main()
