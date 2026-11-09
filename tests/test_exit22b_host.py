"""Acceptance host must send the product's original connection over real local HTTP."""
import copy
import json
import os
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

from ai_union.errors import Rejected
from scripts.exit22b_host import PageHost
from tests.test_work_transport_http import ModeldDouble


CONNECTION = {"id": "saved-connection", "revision": 7, "grant_ref": "adopted-grant",
              "grant_revision": 4, "model": "adopted-model", "max_output_tokens": 37,
              "task_ms": 9000}
PACKAGE = {"kind": "work_step", "work_id": "original-work",
           "attempt_id": "original-work#a1", "run_id": "original-work#s1"}


class HostModeldDouble(ModeldDouble):
    def do_GET(self):
        if self.path == "/v1/accounts":
            type(self).seen.append(("GET", self.path, None, None))
            return self._send(200, {"accounts": [{"id": "selected-account"}]})
        super().do_GET()

    def do_POST(self):
        if self.path == "/v1/grants":
            body = self._body()
            type(self).seen.append(("POST", self.path, None, body))
            return self._send(201, body)
        super().do_POST()


class AcceptanceHostConnectionTests(unittest.TestCase):
    def setUp(self):
        HostModeldDouble.seen = []
        HostModeldDouble.state = "completed"
        HostModeldDouble.post_status = 202
        HostModeldDouble.result = None
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), HostModeldDouble)
        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()

        def close_server():
            self.server.shutdown()
            self.server.server_close()
            thread.join(timeout=5)

        self.addCleanup(close_server)
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.config = self.root / "modeld.json"
        self.config.write_text(json.dumps({
            "origin": "http://127.0.0.1:%d" % self.server.server_address[1],
            "admin_token_file": "admin.token", "worker_token_file": "worker.token",
        }), encoding="utf-8")
        for name in ("admin.token", "worker.token"):
            (self.root / name).write_text("fixture-" + name + "-" + "x" * 40, encoding="utf-8")
        for path in (self.config, self.root / "admin.token", self.root / "worker.token"):
            path.chmod(0o600)
        environment = patch.dict(os.environ, {
            "UNION_MODELD_CONFIG": str(self.config),
            "UNION_REAL_ACCOUNT": "selected-account",
            "UNION_REAL_MODEL": "different-host-model",
        })
        environment.start()
        self.addCleanup(environment.stop)
        self.host = PageHost.__new__(PageHost)
        self.host.app = SimpleNamespace(work=SimpleNamespace())
        self.host.grant_ref = "later-host-grant"
        self.host._wire()

    def chat(self, connection):
        channel = self.host.app.work.transport_factory("original-au", connection)
        return channel.chat(PACKAGE, [{"role": "user", "content": "fixture"}], [])

    def model_posts(self):
        return [row[3] for row in HostModeldDouble.seen
                if row[0:2] == ("POST", "/v1/requests")]

    def test_request_uses_all_adopted_connection_fields(self):
        connection = copy.deepcopy(CONNECTION)
        self.chat(connection)
        body, = self.model_posts()
        self.assertEqual({key: body[key] for key in (
            "au_id", "id", "connection_id", "connection_revision", "grant_ref",
            "grant_revision", "model_id", "generation", "deadlines")}, {
                "au_id": "original-au", "id": "original-work-s1",
                "connection_id": "saved-connection", "connection_revision": 7,
                "grant_ref": "adopted-grant", "grant_revision": 4,
                "model_id": "adopted-model", "generation": {"maxOutputTokens": 37},
                "deadlines": {"first_event_ms": 180000, "idle_ms": 120000, "task_ms": 9000},
            })
        self.assertEqual(connection, CONNECTION)

    def test_later_prepare_for_another_au_cannot_replace_saved_grant(self):
        self.host.prepare("original-au")
        first_grant = self.host.grant_ref
        connection = {**CONNECTION, "grant_ref": first_grant}
        self.host.prepare("another-au")
        self.assertNotEqual(self.host.grant_ref, first_grant)
        self.chat(connection)
        body, = self.model_posts()
        self.assertEqual((body["au_id"], body["grant_ref"]), ("original-au", first_grant))

    def test_missing_fields_cannot_acquire_host_identity_or_limits(self):
        for field in ("id", "revision", "grant_ref", "grant_revision", "model", "max_output_tokens"):
            with self.subTest(field=field):
                connection = copy.deepcopy(CONNECTION)
                del connection[field]
                with self.assertRaises((KeyError, Rejected)):
                    self.chat(connection)
        self.assertEqual(self.model_posts(), [])

    def test_console_restart_needs_no_prepare_to_recover_original_connection(self):
        host = PageHost(self.root / "console")
        self.addCleanup(host.stop)
        host.grant_ref = "stale-host-grant"
        host.restart()
        self.assertEqual(HostModeldDouble.seen, [])
        channel = host.app.work.transport_factory("original-au", copy.deepcopy(CONNECTION))
        self.assertEqual(channel.connection, CONNECTION)
        self.assertEqual(channel.lookup("original-work-s1"), {"input_tokens": 9, "output_tokens": 5})
        self.assertEqual([(r[0], r[1]) for r in HostModeldDouble.seen],
                         [("GET", "/v1/requests/original-work-s1?au_id=original-au")])

    def test_original_lookup_is_scoped_get_without_dispatch_or_new_grant(self):
        channel = self.host.app.work.transport_factory("original-au", copy.deepcopy(CONNECTION))
        self.assertEqual(channel.lookup("original-work-s1"), {"input_tokens": 9, "output_tokens": 5})
        self.assertEqual([(r[0], r[1]) for r in HostModeldDouble.seen],
                         [("GET", "/v1/requests/original-work-s1?au_id=original-au")])

    def test_prepare_rejects_unknown_explicit_account_without_creating_grant(self):
        with patch.dict(os.environ, {"UNION_REAL_ACCOUNT": "not-available"}):
            with self.assertRaisesRegex(SystemExit, "not among the modeld accounts"):
                self.host.prepare("original-au")
        self.assertEqual([(r[0], r[1]) for r in HostModeldDouble.seen], [("GET", "/v1/accounts")])


if __name__ == "__main__":
    unittest.main()
