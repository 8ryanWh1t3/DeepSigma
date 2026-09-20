"""Loopback server and strict JSON behavior. No external network needed."""
import http.client
import json
import threading
import unittest
from http.server import ThreadingHTTPServer

from run import Handler, strict_json
from generate_demo import make_demo


class ServerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.port = cls.server.server_port

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, method, path, body=None, headers=None):
        conn = http.client.HTTPConnection('127.0.0.1', self.port, timeout=5)
        try:
            conn.request(method, path, body=body, headers=headers or {})
            response = conn.getresponse()
            return response.status, response.read(), dict(response.getheaders())
        finally:
            conn.close()

    def test_health_and_evaluate(self):
        status, body, _ = self.request('GET', '/api/health')
        self.assertEqual(status, 200)
        self.assertTrue(json.loads(body)['simulated'])
        status, body, _ = self.request('POST', '/api/evaluate', json.dumps(make_demo()), {'Content-Type': 'application/json'})
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)['diagnostics']['report_count'], 1081)

    def test_asset_and_response_headers(self):
        status, body, headers = self.request('GET', '/engine.js')
        self.assertEqual(status, 200)
        self.assertIn(b'DeepSigmaZipf', body)
        self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])

    def test_invalid_json_and_validation_return_errors(self):
        for body in ['{', '{}', '{"a":1,"a":2}', '{"a":NaN}']:
            with self.subTest(body=body):
                status, result, _ = self.request('POST', '/api/evaluate', body, {'Content-Type': 'application/json'})
                self.assertEqual(status, 400)
                self.assertIn('error', json.loads(result))

    def test_host_origin_and_content_type(self):
        status, _, _ = self.request('GET', '/api/health', headers={'Host': 'untrusted.example'})
        self.assertEqual(status, 403)
        status, _, _ = self.request('POST', '/api/evaluate', '{}', {'Content-Type': 'application/json', 'Origin': 'https://untrusted.example'})
        self.assertEqual(status, 403)
        status, _, _ = self.request('POST', '/api/evaluate', '{}', {'Content-Type': 'text/plain'})
        self.assertEqual(status, 415)

    def test_arbitrary_files_are_not_served(self):
        for path in ['/../README.md', '/data/demo.json', '/run.py', '/%2e%2e/run.py']:
            with self.subTest(path=path):
                status, _, _ = self.request('GET', path)
                self.assertEqual(status, 404)

    def test_strict_json_rejects_duplicate_keys_and_nonfinite(self):
        for raw in ['{"id":1,"id":2}', '{"n":NaN}', '{"n":Infinity}']:
            with self.assertRaises(ValueError):
                strict_json(raw)


if __name__ == '__main__':
    unittest.main()
