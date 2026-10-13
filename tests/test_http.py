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
        connection = http.client.HTTPConnection("127.0.0.1", self.server.server_port, timeout=4)
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
