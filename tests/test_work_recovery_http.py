"""Recovery across real modeld-shaped HTTP and the actual SQLite AU writer."""
import copy
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlsplit
from unittest.mock import patch

from ai_union.adapters.work_execution_store import wire_digest
from ai_union.model_service import ModelServiceClient
from ai_union.work_transport import ModeldWorkTransport
from tests.test_work_recovery import WorkRecoveryTests


class RecoveryModeld(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def send(self, status, body):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self):
        body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        remote = self.server.remote
        remote["posts"].append(copy.deepcopy(body))
        if body["id"] in remote["requests"]:
            return self.send(409, {"error": "duplicate original request"})
        remote["requests"][body["id"]] = body
        if remote["lose_response"]:
            remote["lose_response"] = False
            self.close_connection = True
            return
        self.send(202, {"id": body["id"], "au_id": body["au_id"], "state": "queued"})

    def do_GET(self):
        parts = urlsplit(self.path)
        remote = self.server.remote
        remote["gets"].append(self.path)
        if parts.path.endswith("/events"):
            return self.send(200, {"events": []})
        request_id = parts.path.rsplit("/", 1)[-1]
        body = remote["requests"].get(request_id)
        if body is None:
            return self.send(404, {"error": "missing"})
        au_id = parse_qs(parts.query)["au_id"][0]
        message = remote["message"]
        if message is None:
            if any(m["role"] == "tool" for m in body["messages"]):
                message = {"content": "HTTP recovered final result", "tool_calls": []}
            else:
                message = {"content": None, "tool_calls": [{"id": "http-read", "type": "function",
                    "function": {"name": "read_document", "arguments": '{"path":"nested/a.md"}'}}]}
        self.send(200, {"id": request_id, "au_id": au_id, "request_digest": wire_digest(body),
            "state": "completed", "action_authorized": remote["authorized"],
            "result": {"message": message, "usage": {"input_tokens": 17, "output_tokens": 8}}})


class WorkRecoveryHTTPTests(WorkRecoveryTests):
    def http_channel(self):
        if not hasattr(self, "remote_server"):
            server = self.remote_server = ThreadingHTTPServer(("127.0.0.1", 0), RecoveryModeld)
            server.remote = {"posts": [], "gets": [], "requests": {}, "lose_response": False,
                             "message": None, "authorized": True}
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            def close():
                server.shutdown(); thread.join(5); server.server_close()
            self.addCleanup(close)
            private = self.root / "controlled-modeld"
            private.mkdir()
            (private / "worker.token").write_text("w" * 40, encoding="utf-8")
            (private / "admin.token").write_text("a" * 40, encoding="utf-8")
            self.private_config = private / "modeld.json"
            self.private_config.write_text(json.dumps({
                "origin": "http://127.0.0.1:" + str(server.server_port),
                "worker_token_file": "worker.token", "admin_token_file": "admin.token"}), encoding="utf-8")
            for item in private.iterdir(): item.chmod(0o600)
        connection = self.state()["model_access"]["connections"]["connection-a"]
        self.app.work.transport = ModeldWorkTransport(ModelServiceClient(str(self.private_config)), self.au_id,
                                                      connection, timeout_seconds=5, poll_seconds=0)
        return self.remote_server.remote

    def test_lost_http_post_response_recovers_original_tool_then_reuses_its_saved_text(self):
        request = self.arrange()
        remote = self.http_channel()
        remote["lose_response"] = True
        initial = self.app.work.run_step(self.token, request)
        self.assertEqual(initial["model_outcome"], "unknown")
        first = copy.deepcopy(self.card()["steps"][0])
        self.stop(); self.start()
        self.http_channel()
        _, recovered, _ = self.recover()
        self.assertEqual(recovered["receipt"]["status"], "succeeded", recovered)
        self.assertEqual(len(remote["posts"]), 1)
        self.assertEqual(self.card()["steps"][0]["status"], "used")
        self.assertEqual(self.card()["steps"][0]["step_ref"], first["step_ref"])
        document = self.root / "authorized-docs" / "nested" / "a.md"
        saved_text = document.read_text(encoding="utf-8")
        document.write_text("new bytes after original tool was committed", encoding="utf-8")
        final = self.app.work.run_step(self.token, self.request_value())
        self.assertEqual(final["status"], "succeeded", final)
        self.assertEqual(len(remote["posts"]), 2)
        self.assertNotEqual(remote["posts"][0]["id"], remote["posts"][1]["id"])
        supplied = next(m for m in remote["posts"][1]["messages"] if m["role"] == "tool")
        self.assertEqual(supplied["tool_call_id"], "http-read")
        self.assertEqual(json.loads(supplied["content"])["content"], saved_text)
        self.assertEqual(len(self.card()["attempts"]), 1)
        self.assertEqual(self.card()["results"][0]["content"], "HTTP recovered final result")

    def test_saved_http_observation_is_not_replaced_by_authorization_get_result(self):
        request = self.arrange()
        remote = self.http_channel()
        remote["message"] = {"content": "original privately observed result", "tool_calls": []}
        save = self.app.work.store.save
        def interrupted(cx, state, charter, command, *args, **kwargs):
            if command["kind"] == "work_dispatch_adopted": raise KeyboardInterrupt("controlled adoption crash")
            return save(cx, state, charter, command, *args, **kwargs)
        with patch.object(self.app.work.store, "save", side_effect=interrupted):
            with self.assertRaises(KeyboardInterrupt): self.app.work.run_step(self.token, request)
        self.stop(); self.start()
        self.http_channel()
        remote["message"] = {"content": "must never replace the saved observation", "tool_calls": []}
        _, value, _ = self.recover()
        self.assertEqual(value["receipt"]["status"], "succeeded", value)
        self.assertEqual(self.card()["results"][0]["content"], "original privately observed result")
        self.assertEqual(len(remote["posts"]), 1)

    def test_completed_revoked_http_message_remains_private_with_usage_and_no_tools(self):
        request = self.arrange()
        remote = self.http_channel()
        remote["authorized"] = False
        remote["message"] = {"content": "private revoked completed fact", "tool_calls": []}
        receipt = self.app.work.run_step(self.token, request)
        self.assertEqual(receipt["model_outcome"], "not_adoptable", receipt)
        step = self.card()["steps"][0]
        self.assertEqual(step["status"], "used")
        self.assertEqual(step["usage"], {"input_tokens": 17, "output_tokens": 8})
        self.assertEqual(self.card().get("results", []), [])
        self.assertIsNotNone(step.get("observed_sha256"), "completed message must survive privately before refusal")
        from ai_union.adapters.work_execution_store import WorkExecutionStore
        with self.app.work.store.transaction(self.directory) as cx:
            observed = WorkExecutionStore.load_observed(cx, step)
        self.assertEqual(observed["message"]["content"], "private revoked completed fact")
        self.assertFalse(observed["action_authorized"])
        self.assertNotIn("private revoked completed fact", json.dumps(self.works()))


def load_tests(loader, tests, pattern):
    return unittest.TestSuite(WorkRecoveryHTTPTests(name) for name in WorkRecoveryHTTPTests.__dict__
                             if name.startswith("test_"))
