"""The modeld adapter over a real HTTP loopback server, not a mocked client."""
import json
import tempfile
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

from ai_union.errors import Rejected
from ai_union.model_service import ModelServiceClient, ServiceError
from ai_union.work_transport import ModeldWorkTransport

CONNECTION = {"id": "connection-a", "revision": 2, "grant_ref": "grant-a", "grant_revision": 3,
              "model": "model-a", "max_output_tokens": 1024, "task_ms": 30000}
PACKAGE = {"kind": "work_step", "work_id": "work-overview", "attempt_id": "work-overview#a1",
           "run_id": "work-overview#s1"}
MESSAGE = {"role": "assistant", "content": "# 概览\n"}
USAGE = {"input_tokens": 9, "output_tokens": 5}


class ModeldDouble(BaseHTTPRequestHandler):
    seen = []
    state = "completed"
    post_status = 202

    def log_message(self, *args):  # keep the test output quiet
        pass

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        return json.loads(self.rfile.read(length).decode("utf-8")) if length else None

    def _send(self, status, value):
        data = json.dumps(value).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        body = self._body()
        type(self).seen.append(("POST", self.path, self.headers.get("Authorization"), body))
        self._send(type(self).post_status, {"state": "queued"})

    def do_GET(self):
        parts = urlsplit(self.path)
        type(self).seen.append(("GET", self.path, self.headers.get("Authorization"), None))
        if parts.path.endswith("/events"):
            return self._send(200, {"events": []})
        request_id = parts.path.rsplit("/", 1)[-1]
        result = {"message": MESSAGE, "usage": USAGE} if type(self).state == "completed" else None
        self._send(200, {"id": request_id, "au_id": "au-1", "state": type(self).state, "result": result})


class LoopbackWorkTransportTests(unittest.TestCase):
    def setUp(self):
        ModeldDouble.seen = []
        ModeldDouble.state = "completed"
        ModeldDouble.post_status = 202
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), ModeldDouble)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        (root / "admin.token").write_text("a" * 40, encoding="utf-8")
        (root / "worker.token").write_text("b" * 40, encoding="utf-8")
        self.config = root / "modeld.json"
        self.config.write_text(json.dumps({
            "origin": "http://127.0.0.1:%d" % self.server.server_address[1],
            "admin_token_file": "admin.token", "worker_token_file": "worker.token"}), encoding="utf-8")


    def tearDown(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()
        self.temp.cleanup()

    def transport(self):
        return ModeldWorkTransport(ModelServiceClient(str(self.config)), "au-1", CONNECTION,
                                   sleep=lambda _: None, timeout_seconds=10)

    def test_the_step_travels_over_http_with_the_expected_request_body(self):
        message, usage = self.transport().chat(PACKAGE, [{"role": "user", "content": "目标"}],
                                               [{"type": "function", "function": {"name": "read_document"}}])
        self.assertEqual(message, MESSAGE)
        self.assertEqual(usage, USAGE)
        method, path, authorization, body = ModeldDouble.seen[0]
        self.assertEqual((method, path), ("POST", "/v1/requests"))
        self.assertEqual(authorization, "Bearer " + "b" * 40, "the worker token is the one used for a step")
        self.assertEqual(body["id"], "work-overview-s1")
        self.assertEqual((body["au_id"], body["connection_id"], body["model_id"]), ("au-1", "connection-a", "model-a"))
        self.assertEqual(body["messages"], [{"role": "user", "content": "目标"}])
        self.assertEqual(body["generation"], {"maxOutputTokens": 1024})
        self.assertTrue(any(entry[0] == "GET" and "au_id=au-1" in entry[1] for entry in ModeldDouble.seen))

    def test_an_http_refusal_is_rejected_without_a_step(self):
        ModeldDouble.post_status = 422
        with self.assertRaises(Rejected):
            self.transport().chat(PACKAGE, [], [])

    def test_an_interrupted_request_is_reported_as_unknown(self):
        ModeldDouble.state = "interrupted"
        with self.assertRaises(ServiceError) as caught:
            self.transport().chat(PACKAGE, [], [])
        self.assertIn("interrupted", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
