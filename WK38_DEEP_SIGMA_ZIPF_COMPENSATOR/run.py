#!/usr/bin/env python3
"""Serve the synthetic pilot on loopback. No operational release is performed."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from deep_sigma_zipf.engine import ValidationError, evaluate

ROOT = Path(__file__).resolve().parent
MAX_BODY = 8 * 1024 * 1024
ASSETS = {'/': 'index.html', '/index.html': 'index.html', '/styles.css': 'styles.css',
          '/engine.js': 'engine.js', '/app.js': 'app.js', '/demo.js': 'demo.js'}


def strict_json(raw):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError('Duplicate JSON key: ' + key)
            result[key] = value
        return result
    def invalid_constant(value):
        raise ValueError('Nonfinite JSON number: ' + value)
    return json.loads(raw, object_pairs_hook=pairs, parse_constant=invalid_constant)


class Handler(BaseHTTPRequestHandler):
    server_version = 'DeepSigmaPilot/1.0'

    def send_content(self, status, content, content_type='application/json; charset=utf-8'):
        if not isinstance(content, bytes):
            content = json.dumps(content, ensure_ascii=False, allow_nan=False).encode('utf-8')
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('Content-Security-Policy', "default-src 'self'; script-src 'self'; style-src 'self'; connect-src 'self'; img-src 'self' data:; object-src 'none'; base-uri 'none'; frame-ancestors 'none'")
        self.end_headers()
        self.wfile.write(content)

    def valid_host(self):
        port = self.server.server_port
        return self.headers.get('Host') in {f'127.0.0.1:{port}', f'localhost:{port}'}

    def do_GET(self):
        if not self.valid_host():
            return self.send_content(403, {'error': 'Loopback host required.'})
        path = urlsplit(self.path).path
        if path == '/api/health':
            return self.send_content(200, {'status': 'ok', 'version': '1.0.0', 'simulated': True})
        if path == '/api/demo':
            return self.send_content(200, (ROOT / 'data' / 'demo.json').read_bytes())
        if path in ASSETS:
            target = ROOT / 'web' / ASSETS[path]
            mime = {'css': 'text/css', 'js': 'text/javascript', 'html': 'text/html'}[target.suffix[1:]]
            return self.send_content(200, target.read_bytes(), mime + '; charset=utf-8')
        self.send_content(404, {'error': 'Not found.'})

    def do_POST(self):
        if not self.valid_host():
            return self.send_content(403, {'error': 'Loopback host required.'})
        if urlsplit(self.path).path != '/api/evaluate':
            return self.send_content(404, {'error': 'Not found.'})
        port = self.server.server_port
        origin = self.headers.get('Origin')
        if origin is not None and origin not in {f'http://127.0.0.1:{port}', f'http://localhost:{port}'}:
            return self.send_content(403, {'error': 'Cross-origin evaluation is disabled.'})
        if self.headers.get_content_type() != 'application/json':
            return self.send_content(415, {'error': 'Content-Type must be application/json.'})
        if self.headers.get('Transfer-Encoding'):
            return self.send_content(400, {'error': 'Chunked request bodies are not supported.'})
        try:
            size = int(self.headers.get('Content-Length', '-1'))
        except ValueError:
            return self.send_content(400, {'error': 'Invalid Content-Length.'})
        if size < 0 or size > MAX_BODY:
            return self.send_content(413, {'error': 'JSON body must be at most 8 MiB.'})
        try:
            payload = strict_json(self.rfile.read(size).decode('utf-8'))
            result = evaluate(payload)
        except (ValueError, UnicodeError, ValidationError, RecursionError) as exc:
            return self.send_content(400, {'error': str(exc)})
        self.send_content(200, result)

    def log_message(self, fmt, *args):
        # Do not echo imported payloads or request paths into logs.
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8765)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error('port must be 1..65535')
    try:
        server = ThreadingHTTPServer(('127.0.0.1', args.port), Handler)
    except OSError as exc:
        parser.exit(1, f'Could not start local server: {exc}\nTry --port 8766.\n')
    print(f'DEEP SIGMA ZIPF PILOT 1.0.0\nOpen http://127.0.0.1:{args.port}\nSynthetic evaluation only. Ctrl+C stops the server.', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
