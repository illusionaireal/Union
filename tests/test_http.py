import copy
import http.client
import json
import tempfile
import threading
import unittest
from pathlib import Path

from ai_union.console import Console
from ai_union.server import Server
from tests.support import CHARTER, RESOURCES
from tests.test_console import FIXTURE


class HTTPTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.app = Console(self.temp.name, fixture=copy.deepcopy(FIXTURE))
        self.addCleanup(self.app.close)
        self.server = Server(self.app)
        self.addCleanup(self.server.server_close)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()
        self.addCleanup(thread.join)
        self.addCleanup(self.server.shutdown)
        self.board = self.app.new_session("board")
        self.cookie = self.server.cookie_name + "=" + self.board

    def request(self, method, path, data=None, headers=None, cookie=True):
        headers = {"Origin": self.server.origin, "Content-Type": "application/json"} | (headers or {})
        if cookie:
            headers["Cookie"] = self.cookie
        # Functional fixture calls include SQLite setup on shared CI hosts.
        # Keep a bounded wait without retrying a potentially committed POST.
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=30)
        try:
            connection.request(method, path, body=json.dumps(data) if data is not None else None, headers=headers)
            response = connection.getresponse()
            content = response.read()
            return response.status, json.loads(content) if response.getheader("Content-Type", "").startswith("application/json") else content, dict(response.getheaders())
        finally:
            connection.close()

    def create(self):
        command = {"id": "create-http", "organization_id": None, "base_version": None, "kind": "create",
                   "data": {"name": "http test", "goal": "test", "board_name": "test", "charter": CHARTER, "resources": RESOURCES}}
        status, body, _ = self.request("POST", "/api/commands", command)
        self.assertEqual(status, 200)
        return body["receipt"]["organization_id"]

    def frontend(self):
        static = Path(self.temp.name) / 'frontend'
        (static / 'assets').mkdir(parents=True)
        (static / 'index.html').write_text(
            '<!doctype html><meta http-equiv="Content-Security-Policy" '
            'content="default-src \'none\'; script-src \'self\'"><div id="root"></div>',
            encoding='utf-8')
        self.server.static_dir = static.resolve()
        self.server.document = static / 'index.html'
        return static

    def test_host_origin_cookie_and_observer_cannot_bypass(self):
        self.assertEqual(self.request("GET", "/api/session", cookie=False)[0], 401)
        self.assertEqual(self.request("GET", "/api/session", headers={"Host": "evil.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/commands", {}, headers={"Origin": "http://evil.example"})[0], 403)
        self.assertEqual(self.request("POST", "/api/commands", {}, headers={"Origin": "null"})[0], 403)
        self.assertEqual(self.request("GET", "/api/session", headers={"Sec-Fetch-Site": "cross-site"})[0], 403)
        self.cookie = self.server.cookie_name + "=" + self.app.new_session("observer")
        self.assertEqual(self.request("POST", "/api/commands", {})[0], 403)

    def test_one_time_ticket_http_only_cookie_and_expired_session(self):
        ticket = self.app.ticket("observer")
        status, body, headers = self.request("POST", "/api/session", headers={"X-Union-Launch": ticket}, cookie=False)
        self.assertEqual(status, 200)
        self.assertEqual(body["role"], "observer")
        self.assertIn("HttpOnly", headers["Set-Cookie"])
        self.assertIn("SameSite=Strict", headers["Set-Cookie"])
        self.assertNotIn(ticket, json.dumps(body))
        self.assertEqual(self.request("POST", "/api/session", headers={"X-Union-Launch": ticket})[0], 401)
        self.app.sessions[self.board]["expires"] = 0
        self.assertEqual(self.request("GET", "/api/session")[0], 401)

    def test_commands_and_receipts_survive_reconnect_and_gets_are_readonly(self):
        oid = self.create()
        e = self.app.engine(self.board, oid)
        request = {"id": "start-http", "organization_id": oid, "base_version": 0, "kind": "start", "data": {"executor": "fixture", "max_steps": 8}}
        status, result, _ = self.request("POST", "/api/commands", request)
        self.assertEqual(status, 202)
        self.app.join_jobs()
        self.assertEqual(self.request("POST", "/api/commands", request)[1]["receipt"]["status"], "succeeded")
        before = (e.state(), e.events(), e.runs())
        last = -1
        for _ in range(4):
            status, view, _ = self.request("GET", "/api/snapshot?organization_id=" + oid)
            self.assertEqual(status, 200)
            self.assertGreater(view["snapshot_sequence"], last)
            last = view["snapshot_sequence"]
            self.assertEqual(len(view["organization"]["work"]), 3)
            self.assertEqual(len(view["organization"]["artifacts"]), 3)
            self.assertEqual(view["budget"]["calls_reserved"], 6)
            self.assertNotIn("board.key", json.dumps(view))
            self.assertNotIn("package", view["runs"][0])
        self.assertEqual(before, (e.state(), e.events(), e.runs()))
        aid = next(iter(e.state()["artifacts"]))
        status, content, headers = self.request("GET", f"/api/artifact?organization_id={oid}&id={aid}&download=1")
        self.assertEqual(status, 200)
        self.assertEqual(content.decode("utf-8"), e._read_artifact(e.state()["artifacts"][aid]))
        self.assertIn("attachment", headers["Content-Disposition"])

    def test_spa_routes_and_assets_are_public_same_origin_only(self):
        static = Path(self.temp.name) / 'frontend'
        (static / 'assets').mkdir(parents=True)
        (static / 'index.html').write_text('<!doctype html><div id="root"></div>', encoding='utf-8')
        (static / 'assets' / 'app-test.js').write_text('export const built = true;', encoding='utf-8')
        (static / 'assets' / 'app-test.css').write_text('body{margin:0}', encoding='utf-8')
        (static / 'assets' / 'image.svg').write_text('<svg></svg>', encoding='utf-8')
        (static / 'assets' / 'font.woff2').write_bytes(b'font-fixture')
        (static / 'favicon.svg').write_text('<svg></svg>', encoding='utf-8')
        self.server.static_dir = static.resolve()
        self.server.document = static / 'index.html'
        for path in ('/', '/overview', '/members', '/tasks?organization=example', '/artifacts', '/activity',
                     '/resources', '/settings', '/models', '/gateways'):
            with self.subTest(path=path):
                status, body, headers = self.request('GET', path, cookie=False)
                self.assertEqual(status, 200)
                self.assertIn(b'id="root"', body)
                self.assertIn("script-src 'self'", headers['Content-Security-Policy'])
                self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
                self.assertNotIn('unsafe-inline', headers['Content-Security-Policy'])
        for path, mime in (('/assets/app-test.js', 'text/javascript'), ('/assets/%61pp-test.js', 'text/javascript'),
                           ('/assets/app-test.css', 'text/css'), ('/assets/image.svg', 'image/svg+xml'),
                           ('/assets/font.woff2', 'font/woff2'), ('/favicon.svg', 'image/svg+xml')):
            status, body, headers = self.request('GET', path, cookie=False)
            self.assertEqual(status, 200)
            self.assertTrue(headers['Content-Type'].startswith(mime))
            self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
        self.assertEqual(self.request('GET', '/settings', headers={'Host': 'evil.example'}, cookie=False)[0], 403)
        self.assertEqual(self.request('GET', '/assets/app-test.js', headers={'Sec-Fetch-Site': 'cross-site'}, cookie=False)[0], 403)
        self.assertEqual(self.request('GET', '/api/snapshot', cookie=False)[0], 401)

    def test_v1_spa_routes_serve_public_html_without_reading_au_data(self):
        self.frontend()
        expected = self.server.document.read_bytes()
        # An HTML shell must remain available without reading sessions, AU
        # metadata or business data. Its API calls own those authorization checks.
        self.server.app = None
        paths = (
            '/organizations', '/au/au-test', '/au/au-test/work',
            '/au/au-test/work/work-test', '/au/au-test/results',
            '/au/au-test/work/work-test/results/result-test', '/au/au-test/attention',
            '/au/au-test/resources', '/au/au-test/governance',
            '/au/au-test/improvement', '/au/au-test/collaboration',
            '/au/au-test/work/work-test/results/result-test?organization=other',
        )
        for path in paths:
            with self.subTest(path=path):
                status, body, headers = self.request('GET', path, cookie=False)
                self.assertEqual(status, 200)
                self.assertEqual(body, expected)
                self.assertEqual(headers['Content-Type'], 'text/html; charset=utf-8')
                self.assertEqual(headers['Content-Security-Policy'],
                                 "default-src 'none'; script-src 'self'; frame-ancestors 'none'")
                self.assertEqual(headers['X-Content-Type-Options'], 'nosniff')
                self.assertEqual(headers['X-Frame-Options'], 'DENY')
                self.assertEqual(headers['Referrer-Policy'], 'no-referrer')
                self.assertEqual(headers['Cache-Control'], 'no-store')

    def test_v1_spa_routes_preserve_public_identifier_boundaries(self):
        self.frontend()
        for identifier in ('a', 'Z09_-.version', 'au..core', 'report.json', 'a' + '.' * 79, 'a' * 80,
                           'au%2Ecore', '%61u-test'):
            for path in (f'/au/{identifier}', f'/au/au-test/work/{identifier}',
                         f'/au/au-test/work/work-test/results/{identifier}'):
                with self.subTest(path=path):
                    status, body, _ = self.request('GET', path, cookie=False)
                    self.assertEqual(status, 200)
                    self.assertIn(b'id="root"', body)

    def test_v1_spa_routes_keep_same_origin_boundary(self):
        self.frontend()
        for path in ('/organizations', '/au/au-test',
                     '/au/au-test/work/work-test/results/result-test'):
            for headers in ({'Host': 'evil.example'}, {'Origin': 'http://evil.example'},
                            {'Sec-Fetch-Site': 'cross-site'}):
                with self.subTest(path=path, headers=headers):
                    status, _, response_headers = self.request('GET', path, headers=headers, cookie=False)
                    self.assertEqual(status, 403)
                    self.assertTrue(response_headers['Content-Type'].startswith('application/json'))

    def test_v1_spa_invalid_identifiers_and_undeclared_paths_never_return_html(self):
        self.frontend()
        invalid_ids = (
            '', '.', '..', '.hidden', '-first', '_first', 'a' * 81,
            'two%20words', '%E7%BB%84', 'a%00b', 'a%09b', 'a\\b',
            'a%2fb', 'a%2Fb', 'a%5cb', 'a%5Cb', '%2e', '%2E%2e',
            'bad%', 'bad%2', 'bad%GG', 'bad%FF', 'bad%C3', 'bad%C0%AF',
            'bad%ED%A0%80', 'a%252eb', 'a%252Fb', 'a%255cb',
        )
        paths = [
            '/au', '/au/au-test/', '/organizations/', '/organizations/extra',
            '/au/au-test/unknown', '/au/au-test/work/work-test/extra',
            '/au/au-test/work/work-test/results', '/au/au-test/results/result-test',
            '/au/au-test/work/work-test/results/result-test/extra',
            '/au/au-test/resources/settings', '/au%2fau-test',
            '/au/au-test%2fwork', '/au/au-test/work/work-test%2fresults%2fresult-test',
            '/au/au-test/../organizations', '/au/au-test/./work',
            '/index.html', '/organizations.json', '/au/au-test/index.html',
            '/api', '/api/missing-route', '/api/v1/unknown', '/api/v1/organizations',
        ]
        for identifier in invalid_ids:
            paths.extend((f'/au/{identifier}', f'/au/au-test/work/{identifier}',
                          f'/au/au-test/work/work-test/results/{identifier}'))
        for path in paths:
            with self.subTest(path=path):
                status, _, headers = self.request('GET', path)
                self.assertEqual(status, 404)
                self.assertTrue(headers['Content-Type'].startswith('application/json'))

    def test_static_path_encoding_cannot_resolve_ambiguous_asset_names(self):
        static = self.frontend()
        for name in ('app-test.js', 'bad%.js', 'app%2Ftest.js', 'bad\ufffd.js'):
            (static / 'assets' / name).write_text('private-sentinel', encoding='utf-8')
        for path in ('/assets%2fapp-test.js', '/assets%2Fapp-test.js',
                     '/assets/./app-test.js', '/assets/%2e/app-test.js',
                     '/assets/bad%.js', '/assets/bad%25.js',
                     '/assets/app%252Ftest.js', '/assets/bad%FF.js', '/assets/bad%C3.js'):
            with self.subTest(path=path):
                status, body, headers = self.request('GET', path, cookie=False)
                self.assertEqual(status, 404)
                self.assertNotIn('private-sentinel', json.dumps(body))
                self.assertTrue(headers['Content-Type'].startswith('application/json'))

    def test_static_rejects_duplicate_leading_separators(self):
        static = self.frontend()
        (static / 'assets' / 'app-test.js').write_text('export const built = true;', encoding='utf-8')
        (static / 'favicon.svg').write_text('<svg></svg>', encoding='utf-8')
        for path in ('//', '//organizations', '///organizations',
                     '//organizations?organization=other', '//overview', '//au/a',
                     '//au/a/work/w/results/r', '///au/a/work/w/results/r',
                     '//assets/app-test.js', '///favicon.svg'):
            with self.subTest(path=path):
                status, _, headers = self.request('GET', path, cookie=False)
                self.assertEqual(status, 404)
                self.assertTrue(headers['Content-Type'].startswith('application/json'))

    def test_static_missing_traversal_and_private_files_never_fall_back_to_html(self):
        static = Path(self.temp.name) / 'frontend'
        (static / 'assets').mkdir(parents=True)
        (static / 'index.html').write_text('app shell', encoding='utf-8')
        (static / 'board.key').write_text('private-sentinel', encoding='utf-8')
        (Path(self.temp.name) / 'outside.js').write_text('outside-sentinel', encoding='utf-8')
        self.server.static_dir = static.resolve()
        self.server.document = static / 'index.html'
        for path in ('/assets/missing.js', '/board.key', '/src/main.tsx', '/missing-route', '/assets/../board.key',
                     '/assets/%2e%2e/board.key', '/assets/%2e%2e/%2e%2e/outside.js', '/assets/%5c..%5cboard.key',
                     '/assets/null%00.js', '/assets/'):
            with self.subTest(path=path):
                status, body, headers = self.request('GET', path, cookie=False)
                self.assertEqual(status, 404)
                self.assertNotIn('sentinel', json.dumps(body))
                self.assertTrue(headers['Content-Type'].startswith('application/json'))
        self.server.document.unlink()
        self.assertEqual(self.request('GET', '/settings', cookie=False)[0], 503)
