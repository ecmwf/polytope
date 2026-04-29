import argparse
import json
import logging
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from polytope_feature.datacube.switching_grid_local import lookup_grid_config_local


class SwitchingGridHandler(BaseHTTPRequestHandler):
    def _send_json(self, status, payload):
        body = json.dumps(payload).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        if self.path.rstrip('/') != '/lookup-grid-config':
            self._send_json(404, {'error': 'not found'})
            return

        try:
            content_length = int(self.headers.get('Content-Length', '0'))
            raw = self.rfile.read(content_length)
            payload = json.loads(raw.decode('utf-8') or '{}')
            req = payload.get('request', payload)
            gridspec, md5hash = lookup_grid_config_local(req)
            self._send_json(200, {'gridspec': gridspec, 'md5hash': md5hash})
        except Exception as exc:
            logging.exception('lookup-grid-config failed')
            self._send_json(500, {'error': str(exc)})

    def do_GET(self):
        if self.path.rstrip('/') == '/healthz':
            self._send_json(200, {'ok': True})
            return
        self._send_json(404, {'error': 'not found'})

    def log_message(self, format, *args):
        logging.info('%s - %s', self.address_string(), format % args)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='127.0.0.1')
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    server = ThreadingHTTPServer((args.host, args.port), SwitchingGridHandler)
    logging.info('Starting switching-grid service on %s:%s', args.host, args.port)
    server.serve_forever()


if __name__ == '__main__':
    main()
